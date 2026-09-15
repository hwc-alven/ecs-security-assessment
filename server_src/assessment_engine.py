import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from .ssh_service import SSHService
from .rag_service import RAGService
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class AssessmentEngine:
    """Orchestrates the security hardening assessment workflow."""

    def __init__(
        self,
        ssh_service: SSHService,
        rag_service: RAGService,
        llm_service: LLMService,
    ):
        self.ssh = ssh_service
        self.rag = rag_service
        self.llm = llm_service
        self._cancel_event: Optional[threading.Event] = None

    def set_cancel_event(self, event: threading.Event):
        """Set a threading.Event that, when set, cancels the assessment."""
        self._cancel_event = event

    def _is_cancelled(self) -> bool:
        return self._cancel_event is not None and self._cancel_event.is_set()

    def assess_server(
        self,
        server: Dict,
        benchmark: str,
        log_cb: Optional[Callable[[str], None]] = None,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> Dict:
        """Assess a single server against a benchmark."""
        host = server["ip"]
        port = server.get("ssh_port", 22)
        username = server.get("ssh_username", "root")

        def emit_log(msg: str):
            ts = datetime.now().strftime("%H:%M:%S")
            formatted = f"[{ts}] {msg}"
            logger.info(formatted)
            if log_cb:
                log_cb(formatted)

        result = {
            "server_ip": host,
            "ssh_port": port,
            "username": username,
            "benchmark": benchmark,
            "status": "pending",
            "controls_assessed": [],
            "error": None,
        }

        try:
            # Step 1: Connect via SSH
            emit_log(f"🔌 Connecting to {username}@{host}:{port} via SSH...")
            client = self.ssh.connect(host, port, username)
            result["status"] = "connected"
            emit_log(f"✅ SSH connection established to {host}:{port}")

            # Step 2: Collect VM configuration
            emit_log(f"📥 Collecting read-only security configuration from {host}...")
            config_data = self.ssh.collect_vm_config(client)
            client.close()
            result["config_collected"] = True
            emit_log(f"✅ Configuration data collected successfully from {host}")

            # Step 3: Get benchmark controls from RAG
            emit_log(f"📚 Fetching {benchmark} benchmark controls from RAG...")
            controls = self.rag.get_benchmark_controls(benchmark)
            if not controls:
                result["status"] = "failed"
                result["error"] = f"No {benchmark} benchmark controls found"
                emit_log(f"❌ No {benchmark} controls found")
                return result

            total_c = len(controls)
            emit_log(f"🤖 Starting LLM analysis for {total_c} security controls (parallel, 3 at a time)...")

            # Step 4: Analyze controls with LLM in parallel (3 concurrent calls to avoid rate limiting)
            result["status"] = "analyzing"
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def _analyze_one(idx_control):
                idx, control = idx_control
                if self._is_cancelled():
                    return idx, control, None
                c_title = control.get("title", "N/A")
                rag_context = self.rag.search(
                    query=f"{c_title} {control.get('description', '')}",
                    benchmark=benchmark,
                    top_k=3,
                )
                analysis = self.llm.analyze_control(control, config_data, rag_context)
                return idx, control, analysis

            completed_count = 0
            with ThreadPoolExecutor(max_workers=3) as llm_executor:
                futures = {
                    llm_executor.submit(_analyze_one, (idx, control)): idx
                    for idx, control in enumerate(controls)
                }
                for future in as_completed(futures):
                    if self._is_cancelled():
                        result["status"] = "cancelled"
                        emit_log(f"⏹️ Assessment cancelled by user during LLM analysis")
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        return result

                    idx, control, analysis = future.result()
                    if analysis is None:
                        continue

                    c_id = control.get("id", "N/A")
                    c_title = control.get("title", "N/A")
                    result["controls_assessed"].append(analysis)

                    completed_count += 1
                    comp = analysis.get("compliant")
                    symbol = "✅ PASS" if comp is True else "❌ NON-COMPLIANT" if comp is False else "⚠️ UNKNOWN"
                    emit_log(f"  [{completed_count}/{total_c}] {symbol} [{c_id}] {c_title[:50]} — Risk: {analysis.get('risk_level', 'N/A')}")

                    if progress_cb:
                        progress_cb(int(10 + (completed_count / total_c) * 85))

            # Sort results by original control order
            result["controls_assessed"].sort(
                key=lambda x: next((i for i, c in enumerate(controls) if c.get("id") == x.get("control_id")), 0)
            )

            result["status"] = "completed"
            emit_log(f"🎉 Assessment completed successfully for {host}!")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            emit_log(f"💥 Assessment failed for {host}: {e}")

        return result

    def assess_task(
        self,
        servers: List[Dict],
        benchmark: str,
        max_workers: int = 10,
        log_cb: Optional[Callable[[str], None]] = None,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> Dict:
        """Assess multiple servers in parallel for a single task."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def emit_log(msg: str):
            ts = datetime.now().strftime("%H:%M:%S")
            formatted = f"[{ts}] {msg}"
            logger.info(formatted)
            if log_cb:
                log_cb(formatted)

        emit_log(f"🚀 Initializing assessment task across {len(servers)} server(s) using {benchmark} benchmark...")

        task_result = {
            "benchmark": benchmark,
            "total_servers": len(servers),
            "server_results": [None] * len(servers),
            "summary": {},
        }

        with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(servers)))) as executor:
            future_to_idx = {
                executor.submit(self.assess_server, server, benchmark, log_cb, progress_cb): idx
                for idx, server in enumerate(servers)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    task_result["server_results"][idx] = future.result()
                except Exception as e:
                    task_result["server_results"][idx] = {
                        "server_ip": servers[idx]["ip"],
                        "benchmark": benchmark,
                        "status": "failed",
                        "controls_assessed": [],
                        "error": str(e),
                    }

        total_controls = sum(len(r.get("controls_assessed", [])) for r in task_result["server_results"])
        compliant = sum(1 for r in task_result["server_results"] for c in r.get("controls_assessed", []) if c.get("compliant") is True)
        non_compliant = sum(1 for r in task_result["server_results"] for c in r.get("controls_assessed", []) if c.get("compliant") is False)
        unknown = sum(1 for r in task_result["server_results"] for c in r.get("controls_assessed", []) if c.get("compliant") is None)

        # Compliance rate is based on controls that could be determined (not unknown)
        determined = compliant + non_compliant
        compliance_rate = f"{(compliant / determined * 100 if determined > 0 else 0):.1f}%"

        task_result["summary"] = {
            "total_servers": len(servers),
            "successful": sum(1 for r in task_result["server_results"] if r.get("status") == "completed"),
            "failed": sum(1 for r in task_result["server_results"] if r.get("status") != "completed"),
            "total_controls": total_controls,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "unknown": unknown,
            "compliance_rate": compliance_rate,
        }

        # Check if any server was cancelled
        any_cancelled = any(r.get("status") == "cancelled" for r in task_result["server_results"])
        if any_cancelled:
            task_result["cancelled"] = True

        emit_log(f"📊 Summary: {task_result['summary']['successful']}/{len(servers)} servers succeeded. Compliance Rate: {task_result['summary']['compliance_rate']}")
        return task_result


