"""LLM service — analyzes VM security controls using an OpenAI-compatible LLM API.

Sends benchmark control definitions + collected server configuration data to the
LLM and parses the structured JSON response into a compliance result dict.
"""
import json
import logging
import re
import time
import random
from typing import Dict, List, Optional
import openai

from ..config import AVAILABLE_MODELS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior Linux server security assessment expert specializing in cloud VM hardening.

You analyze server configurations against security benchmarks (CIS, STIG, NIST, PCI-DSS) and determine compliance.

For each control, you will:
1. Examine the provided server configuration data
2. Determine if the control is compliant, non-compliant, or unknown (insufficient data)
3. Identify the current value found in the configuration
4. Explain your analysis clearly
5. Provide a specific, actionable remediation suggestion if non-compliant

You must respond with valid JSON only. No markdown, no code fences, no extra text before or after the JSON.

Response format (example):
{"compliant": false, "current_value": "PermitRootLogin yes", "expected_value": "PermitRootLogin no", "risk_level": "High", "analysis": "PermitRootLogin is set to yes, allowing direct root SSH login", "suggestion": "Edit /etc/ssh/sshd_config and set PermitRootLogin no, then restart sshd"}

Rules:
- "compliant": true if the control is met, false if not, null if you truly cannot determine
- "risk_level": High for security-critical controls (SELinux, firewall, SSH, passwords), Medium for important configs, Low for minor hardening
- "current_value": extract the actual value from the config data, not a generic statement
- "analysis": explain what you found and why it is or isn't compliant
- "suggestion": provide specific commands or config changes to fix the issue, empty string if already compliant

IMPORTANT - Handling missing data:
- If a specific config section shows an error or is unavailable, check whether the control can be assessed from OTHER available data sections first
- Do NOT return compliant: null simply because one data source is missing — cross-reference other sections
- Only return compliant: null if you have examined ALL available data and truly cannot determine compliance
- If config data contains "ChannelException" or "Connect failed" errors, treat that specific section as unavailable but still check other sections
- When examining SSH config, check BOTH sshd_config AND sshd_config_d sections, as settings may be in either
- When examining PAM/password policy, check login_defs, pam_password, pam_system_auth, AND pwquality_conf sections
- When examining file permissions, check shadow_perms section for actual permission values
"""


class LLMService:
    """LLM service for analyzing VM security controls."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api-ap-southeast-1.modelarts-maas.com/v2",
        model: str = "glm-5.2",
        temperature: float = 0.1,
    ):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self._config_summary_cache: Optional[str] = None
        self._config_data_hash: Optional[str] = None
        self._last_request_time: float = 0.0
        self._min_request_interval: float = 0.5

    def _throttle(self):
        """Ensure minimum interval between API requests to avoid rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            wait = self._min_request_interval - elapsed
            time.sleep(wait)
        self._last_request_time = time.time()

    def chat(self, messages: List[Dict], timeout: int = 90, max_tokens: int = 2048) -> str:
        """Send a chat completion request and return the text response."""
        self._throttle()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def analyze_control(
        self,
        control: Dict,
        config_data: Dict,
        rag_context: Optional[List[Dict]] = None,
    ) -> Dict:
        """Analyze a single security control against collected server config data."""
        config_summary = self._get_config_summary(config_data)

        control_text = f"""Control ID: {control.get('id', 'N/A')}
Title: {control.get('title', 'N/A')}
Description: {control.get('description', 'N/A')}
Expected: {control.get('expected', 'N/A')}
Severity: {control.get('severity', 'N/A')}
Category: {control.get('category', 'N/A')}
"""

        rag_text = ""
        if rag_context:
            rag_text = "\n\nRelated benchmark context:\n"
            for ctx in rag_context[:3]:
                rag_text += f"- {ctx.get('control_id', '')}: {ctx.get('title', '')} — {ctx.get('expected', '')}\n"

        user_prompt = f"""Analyze the following security control against the server configuration data.

{control_text}
{rag_text}

Server Configuration Data:
{config_summary}

Determine if this control is compliant. Respond with JSON only, no markdown, no code fences."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        MAX_LLM_RETRIES = 5
        last_error = None

        for attempt in range(MAX_LLM_RETRIES):
            try:
                if attempt >= 2:
                    simple_prompt = f"""Analyze this security control. Respond with ONLY a JSON object, no other text.

Control: {control.get('id', 'N/A')} - {control.get('title', 'N/A')}
Expected: {control.get('expected', 'N/A')}

Server Configuration Data:
{config_summary}

JSON format required:
{{"compliant": true/false/null, "current_value": "...", "expected_value": "...", "risk_level": "High/Medium/Low", "analysis": "...", "suggestion": "..."}}"""
                    messages = [
                        {"role": "system", "content": "You are a security assessment expert. Output ONLY valid JSON, no markdown, no code fences, no extra text."},
                        {"role": "user", "content": simple_prompt},
                    ]

                raw = self.chat(messages, max_tokens=2048)
                result = self._parse_response(raw)

                if result.get("current_value") == "N/A" and result.get("compliant") is None and attempt < MAX_LLM_RETRIES - 1:
                    logger.warning("LLM parse fallback for %s (attempt %d/%d), raw[:200]=%s",
                                   control.get('id', '?'), attempt + 1, MAX_LLM_RETRIES, (raw or '')[:200])
                    backoff = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(backoff)
                    continue

                result["control_id"] = control.get("id", "")
                result["control_title"] = control.get("title", "")
                return result
            except openai.RateLimitError as e:
                last_error = e
                backoff = 5.0 * (2 ** attempt) + random.uniform(0, 2)
                logger.warning("Rate limited on %s (attempt %d/%d), waiting %.1fs",
                               control.get('id', '?'), attempt + 1, MAX_LLM_RETRIES, backoff)
                time.sleep(backoff)
                continue
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    backoff = 5.0 * (2 ** attempt) + random.uniform(0, 2)
                else:
                    backoff = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                logger.error("LLM analysis failed for %s (attempt %d/%d): %s, waiting %.1fs",
                             control.get('id', '?'), attempt + 1, MAX_LLM_RETRIES, err_str[:200], backoff)
                if attempt < MAX_LLM_RETRIES - 1:
                    time.sleep(backoff)
                    continue

        return {
            "control_id": control.get("id", ""),
            "control_title": control.get("title", ""),
            "compliant": None,
            "current_value": "N/A",
            "expected_value": control.get("expected", "N/A"),
            "risk_level": control.get("severity", "Unknown"),
            "analysis": f"LLM analysis failed after {MAX_LLM_RETRIES} retries: {last_error}",
            "suggestion": "",
        }

    def _get_config_summary(self, config_data: Dict) -> str:
        """Get config summary with caching."""
        import hashlib
        data_str = json.dumps(config_data, sort_keys=True, default=str)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        if self._config_summary_cache and self._config_data_hash == data_hash:
            return self._config_summary_cache
        summary = self._build_config_summary(config_data)
        self._config_summary_cache = summary
        self._config_data_hash = data_hash
        return summary

    def _build_config_summary(self, config_data: Dict) -> str:
        """Build a readable summary of VM configuration data for the LLM prompt."""
        if not config_data:
            return "No configuration data collected."

        HIGH_PRIORITY_SECTIONS = {
            "SSH Configuration", "Password & PAM Policy", "SELinux / AppArmor",
            "Firewall", "Auditing & Logging", "File Permissions & Security",
        }
        HIGH_PRIORITY_LIMIT = 3000
        DEFAULT_LIMIT = 2000

        sections = [
            ("OS & Kernel", ["os_info", "kernel_info", "uptime", "hostname"]),
            ("Filesystem & Mounts", [
                "mount_info", "fstab", "disk_usage",
                "tmp_mount_opts", "var_mount_opts", "var_log_mount_opts",
                "home_mount_opts", "var_log_audit_mount_opts",
            ]),
            ("SSH Configuration", ["sshd_config", "sshd_config_d"]),
            ("Password & PAM Policy", [
                "login_defs", "pam_password", "pam_system_auth", "pwquality_conf",
            ]),
            ("SELinux / AppArmor", [
                "selinux_status", "selinux_config", "apparmor_status",
            ]),
            ("Firewall", [
                "firewalld_status", "iptables_status", "nftables_status", "ufw_status",
            ]),
            ("Network & Ports", [
                "open_ports", "listening_udp", "network_interfaces", "ip6_enabled",
            ]),
            ("Services", [
                "running_services", "enabled_services",
                "telnet_service", "rsh_service",
            ]),
            ("Users & Accounts", [
                "passwd_file", "shadow_perms", "uid_zero_accounts",
                "users_with_shells", "sudoers", "sudoers_d",
                "cron_allow", "cron_deny",
            ]),
            ("File Permissions & Security", [
                "world_writable_files", "world_writable_dirs_no_sticky",
                "suid_files", "sgid_files",
            ]),
            ("Auditing & Logging", [
                "auditd_status", "auditd_config", "audit_rules",
                "rsyslog_status", "rsyslog_config",
            ]),
            ("Kernel Hardening (sysctl)", [
                "sysctl_security", "sysctl_network",
            ]),
            ("Time Synchronization", ["chrony_status", "ntp_status"]),
            ("FIPS / Crypto", ["fips_status", "fips_check"]),
            ("Package Updates", ["yum_updates", "dnf_updates", "apt_updates"]),
            ("Bootloader", ["grub_config"]),
            ("USB / Bluetooth", ["usb_storage", "bluetooth_service"]),
            ("X Windows", ["xwindows_check"]),
            ("Intrusion Detection", ["fail2ban_status", "aide_check", "clamav_check"]),
            ("Core Dump Settings", ["limits_conf", "ulimit_core"]),
        ]

        lines = []
        for section_name, keys in sections:
            section_lines = []
            trunc_limit = HIGH_PRIORITY_LIMIT if section_name in HIGH_PRIORITY_SECTIONS else DEFAULT_LIMIT
            for key in keys:
                entry = config_data.get(key)
                if not entry:
                    continue
                output = ""
                if isinstance(entry, dict):
                    output = entry.get("output", "") or entry.get("error", "")
                elif isinstance(entry, str):
                    output = entry
                if output:
                    if len(output) > trunc_limit:
                        output = output[:trunc_limit] + "\n... (truncated)"
                    section_lines.append(f"  [{key}]\n{output}")

            if section_lines:
                lines.append(f"=== {section_name} ===")
                lines.extend(section_lines)
                lines.append("")

        return "\n".join(lines) if lines else "No configuration data collected."

    def _parse_response(self, raw: str) -> Dict:
        """Parse the LLM JSON response with robust multi-strategy parsing."""
        if not raw or not raw.strip():
            logger.warning("Empty LLM response")
            return self._parse_fallback(raw)

        text = raw.strip()

        # Strategy 1: Strip markdown code fences
        if "```" in text:
            text = re.sub(r'```(?:json|JSON|python)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
            text = text.strip()

        # Strategy 2: Try direct JSON parse
        try:
            return self._validate_result(json.loads(text))
        except json.JSONDecodeError:
            pass

        # Strategy 2b: Fix common JSON issues and retry
        fixed = self._fix_json(text)
        if fixed != text:
            try:
                return self._validate_result(json.loads(fixed))
            except json.JSONDecodeError:
                pass

        # Strategy 3: Balanced-brace scanner
        json_block = self._extract_json_balanced(text)
        if json_block:
            try:
                return self._validate_result(json.loads(json_block))
            except json.JSONDecodeError:
                fixed_block = self._fix_json(json_block)
                try:
                    return self._validate_result(json.loads(fixed_block))
                except json.JSONDecodeError:
                    pass

        # Strategy 4: Try progressively from each '{'
        for i, ch in enumerate(text):
            if ch == '{':
                for j in range(len(text), i, -1):
                    try:
                        candidate = text[i:j]
                        return self._validate_result(json.loads(candidate))
                    except json.JSONDecodeError:
                        continue

        # Strategy 5: Regex-based extraction from non-JSON text
        regex_result = self._regex_extract(text)
        if regex_result:
            return regex_result

        return self._parse_fallback(raw)

    def _fix_json(self, text: str) -> str:
        """Fix common JSON formatting issues from LLM responses."""
        # Remove trailing commas before } or ]
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        # Replace single quotes with double quotes (if not inside double-quoted strings)
        if "'" in text and '"' not in text:
            text = text.replace("'", '"')
        # Replace Python-style True/False/None with JSON true/false/null
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        text = re.sub(r'\bNone\b', 'null', text)
        # Remove control characters that break JSON
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text

    def _validate_result(self, result: Dict) -> Dict:
        """Validate and normalize parsed result."""
        if not isinstance(result, dict):
            return self._parse_fallback(str(result))
        # Ensure required keys exist
        if "compliant" not in result:
            result["compliant"] = None
        if "current_value" not in result:
            result["current_value"] = "N/A"
        if "expected_value" not in result:
            result["expected_value"] = "N/A"
        if "risk_level" not in result:
            result["risk_level"] = "Unknown"
        if "analysis" not in result:
            result["analysis"] = ""
        if "suggestion" not in result:
            result["suggestion"] = ""
        return result

    def _regex_extract(self, text: str) -> Optional[Dict]:
        """Last-resort regex extraction of compliance info from non-JSON text."""
        result = {}
        # Extract compliant status
        comp_match = re.search(r'"?compliant"?\s*[:=]\s*(true|false|null|none|yes|no)', text, re.IGNORECASE)
        if comp_match:
            val = comp_match.group(1).lower()
            if val in ('true', 'yes'):
                result["compliant"] = True
            elif val in ('false', 'no'):
                result["compliant"] = False
            else:
                result["compliant"] = None
        else:
            return None

        # Extract current_value
        cv_match = re.search(r'"?current_value"?\s*[:=]\s*"?([^",\n}]+)"?', text)
        if cv_match:
            result["current_value"] = cv_match.group(1).strip()

        # Extract expected_value
        ev_match = re.search(r'"?expected_value"?\s*[:=]\s*"?([^",\n}]+)"?', text)
        if ev_match:
            result["expected_value"] = ev_match.group(1).strip()

        # Extract risk_level
        rl_match = re.search(r'"?risk_level"?\s*[:=]\s*"?([^",\n}]+)"?', text, re.IGNORECASE)
        if rl_match:
            result["risk_level"] = rl_match.group(1).strip()

        # Extract analysis
        an_match = re.search(r'"?analysis"?\s*[:=]\s*"?([^"}]+)"?', text)
        if an_match:
            result["analysis"] = an_match.group(1).strip()

        # Extract suggestion
        sg_match = re.search(r'"?suggestion"?\s*[:=]\s*"?([^"}]+)"?', text)
        if sg_match:
            result["suggestion"] = sg_match.group(1).strip()

        return result if "compliant" in result else None

    def _extract_json_balanced(self, text: str) -> Optional[str]:
        """Extract the outermost balanced JSON object using a brace counter."""
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _parse_fallback(self, raw: str) -> Dict:
        """Return unknown result when all parsing strategies fail."""
        logger.warning("Could not parse LLM response as JSON: %s", (raw or '')[:300])
        return {
            "compliant": None,
            "current_value": "N/A",
            "expected_value": "N/A",
            "risk_level": "Unknown",
            "analysis": f"Failed to parse LLM response: {(raw or '')[:200]}",
            "suggestion": "",
        }

    def generate_report_summary(self, server_results: List[Dict]) -> str:
        """Generate an executive summary of the assessment results using the LLM."""
        total_servers = len(server_results)
        successful = sum(1 for r in server_results if r.get("status") == "completed")
        all_controls = [c for r in server_results for c in r.get("controls_assessed", [])]
        total_controls = len(all_controls)
        compliant = sum(1 for c in all_controls if c.get("compliant") is True)
        non_compliant = sum(1 for c in all_controls if c.get("compliant") is False)
        unknown = sum(1 for c in all_controls if c.get("compliant") is None)

        failed_controls = [c for c in all_controls if c.get("compliant") is False]
        failed_titles = list(set(c.get("control_title", "") for c in failed_controls))[:15]

        stats_text = f"""Assessment Statistics:
- Total servers assessed: {total_servers}
- Successful assessments: {successful}
- Total controls evaluated: {total_controls}
- Compliant: {compliant}
- Non-compliant: {non_compliant}
- Unknown: {unknown}

Top non-compliant controls:
{chr(10).join(f'- {t}' for t in failed_titles) if failed_titles else '- None'}
"""

        prompt = f"""You are a senior Linux server security assessment expert. Based on the following assessment statistics, write a concise executive summary (3-5 paragraphs) for a VM security hardening assessment report.

{stats_text}

The summary should:
1. State the overall security posture and compliance rate
2. Highlight the most critical findings and risks
3. Identify patterns or systemic issues
4. Provide high-level recommendations for improving the security posture

Write in a professional tone suitable for a technical report. Do not use markdown formatting."""

        try:
            messages = [
                {"role": "system", "content": "You are a senior Linux server security assessment expert."},
                {"role": "user", "content": prompt},
            ]
            return self.chat(messages, max_tokens=2048)
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return f"Executive summary generation failed. Stats: {stats_text}"

    def analyze_custom_checklist(self, items: List[Dict]) -> Dict:
        """Analyze a custom checklist using the LLM."""
        items_text = json.dumps(items[:50], indent=2, ensure_ascii=False)

        prompt = f"""You are a senior Linux server security assessment expert. Analyze the following custom security checklist items and provide an assessment.

Checklist Items:
{items_text}

Respond with JSON only:
{{
    "overall_assessment": "summary of the checklist quality and coverage",
    "missing_controls": ["list of important controls that are missing"],
    "recommendations": ["list of specific recommendations to improve the checklist"]
}}"""

        try:
            raw = self.chat([
                {"role": "system", "content": "You are a senior Linux server security assessment expert."},
                {"role": "user", "content": prompt},
            ])
            return self._parse_response(raw)
        except Exception as e:
            logger.error(f"Custom checklist analysis failed: {e}")
            return {
                "overall_assessment": f"Analysis failed: {e}",
                "missing_controls": [],
                "recommendations": [],
            }