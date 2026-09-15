# AI生成
"""LLM service — analyzes VM security controls using an OpenAI-compatible LLM API.

Sends benchmark control definitions + collected server configuration data to the
LLM and parses the structured JSON response into a compliance result dict.
"""
import json
import logging
import re
from typing import Dict, List, Optional
import openai

from ..config import AVAILABLE_MODELS

logger = logging.getLogger(__name__)

# ============================================================
# System prompt for VM security assessment
# ============================================================

SYSTEM_PROMPT = """You are a senior Linux server security assessment expert specializing in cloud VM hardening.

You analyze server configurations against security benchmarks (CIS, STIG, NIST, PCI-DSS) and determine compliance.

For each control, you will:
1. Examine the provided server configuration data
2. Determine if the control is compliant, non-compliant, or unknown (insufficient data)
3. Identify the current value found in the configuration
4. Explain your analysis clearly
5. Provide a specific, actionable remediation suggestion if non-compliant

You must respond with valid JSON only, no markdown formatting, no code blocks, no extra text.

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

    def chat(self, messages: List[Dict], timeout: int = 60) -> str:
        """Send a chat completion request and return the text response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            timeout=timeout,
        )
        return response.choices[0].message.content

    def analyze_control(
        self,
        control: Dict,
        config_data: Dict,
        rag_context: Optional[List[Dict]] = None,
    ) -> Dict:
        """Analyze a single security control against collected server config data.

        Args:
            control: benchmark control definition (id, title, description, expected, etc.)
            config_data: dict of command results from collect_vm_config()
            rag_context: optional RAG-retrieved related controls for context

        Returns:
            dict with compliant, current_value, expected_value, risk_level, analysis, suggestion
        """
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

Determine if this control is compliant. Respond with JSON only."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Fix 4: Retry LLM calls with backoff (up to 3 attempts)
        import time as _time
        MAX_LLM_RETRIES = 3
        last_error = None

        for attempt in range(MAX_LLM_RETRIES):
            try:
                if attempt == 2:
                    # On last attempt, use a simplified prompt for better success rate
                    simple_prompt = f"""Analyze this security control and respond with JSON only.

Control: {control.get('id', 'N/A')} - {control.get('title', 'N/A')}
Expected: {control.get('expected', 'N/A')}

Server Configuration Data:
{config_summary}

Respond with this JSON format only:
{{"compliant": true/false/null, "current_value": "...", "expected_value": "...", "risk_level": "High/Medium/Low", "analysis": "...", "suggestion": "..."}}"""
                    messages = [
                        {"role": "system", "content": "You are a security assessment expert. Respond with valid JSON only."},
                        {"role": "user", "content": simple_prompt},
                    ]

                raw = self.chat(messages)
                result = self._parse_response(raw)

                # Check if parsing failed (all defaults returned)
                if result.get("current_value") == "N/A" and result.get("compliant") is None and attempt < MAX_LLM_RETRIES - 1:
                    logger.warning(f"LLM response parse failed for control {control.get('id', '?')} (attempt {attempt + 1}/{MAX_LLM_RETRIES}), retrying...")
                    _time.sleep(1 * (2 ** attempt))  # 1s, 2s backoff
                    continue

                result["control_id"] = control.get("id", "")
                result["control_title"] = control.get("title", "")
                return result
            except Exception as e:
                last_error = e
                logger.error(f"LLM analysis failed for control {control.get('id', '?')} (attempt {attempt + 1}/{MAX_LLM_RETRIES}): {e}")
                if attempt < MAX_LLM_RETRIES - 1:
                    _time.sleep(1 * (2 ** attempt))  # 1s, 2s backoff
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
        """Get config summary with caching — avoids rebuilding the same summary for every control."""
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
        """Build a readable summary of VM configuration data for the LLM prompt.

        Groups the collected command outputs into logical sections so the LLM
        can efficiently reason about the server's security posture.
        Uses higher truncation limits for security-critical sections.
        """
        if not config_data:
            return "No configuration data collected."

        # Security-critical sections get higher truncation limits
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
                    # Truncate very long outputs to keep prompt manageable
                    if len(output) > trunc_limit:
                        output = output[:trunc_limit] + "\n... (truncated)"
                    section_lines.append(f"  [{key}]\n{output}")

            if section_lines:
                lines.append(f"=== {section_name} ===")
                lines.extend(section_lines)
                lines.append("")

        return "\n".join(lines) if lines else "No configuration data collected."

    def _parse_response(self, raw: str) -> Dict:
        """Parse the LLM JSON response with robust multi-strategy parsing.

        Handles markdown code fences, extra commentary, deeply nested JSON,
        and various model-specific response formats.
        """
        if not raw or not raw.strip():
            logger.warning("Empty LLM response")
            return self._parse_fallback(raw)

        text = raw.strip()

        # Strategy 1: Strip markdown code fences (```json, ```JSON, ```, etc.)
        if "```" in text:
            # Remove all code fence markers
            text = re.sub(r'```(?:json|JSON)?\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
            text = text.strip()

        # Strategy 2: Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Balanced-brace scanner — find outermost {...} block
        json_block = self._extract_json_balanced(text)
        if json_block:
            try:
                return json.loads(json_block)
            except json.JSONDecodeError:
                pass

        # Strategy 4: Try progressively from each '{' found in text
        for i, ch in enumerate(text):
            if ch == '{':
                for j in range(len(text), i, -1):
                    try:
                        candidate = text[i:j]
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue

        # All strategies failed
        return self._parse_fallback(raw)

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
        logger.warning(f"Could not parse LLM response as JSON: {raw[:200]}")
        return {
            "compliant": None,
            "current_value": "N/A",
            "expected_value": "N/A",
            "risk_level": "Unknown",
            "analysis": f"Failed to parse LLM response: {raw[:200]}",
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

        # Collect non-compliant control titles for the summary
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
            return self.chat(messages)
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
