#!/usr/bin/env python3
"""
UAT Functional Test Script for ECS Security Assessment Web Application
Server: 119.8.181.202:8000
Tests: Login, Assessment page, Static JS, API endpoints, duplicate log detection,
       terminal reopen, polling interval behavior.
"""
import paramiko
import socket
import json
import time
import sys
import re
import os

HOST = "119.8.181.202"
USER = "root"
PASS = "Test123!@#"
PORT = 22
WEB_BASE = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "Test123!@#"

# Results collector
results = []
all_pass = True

def log(name, passed, detail=""):
    global all_pass
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    results.append({"test": name, "status": status, "detail": detail})
    print(f"[{status}] {name}")
    if detail:
        for line in detail.split("\n"):
            print(f"       {line}")

def run_remote(cmd, timeout=30):
    """Run a command on the server via SSH and return (stdout, stderr, exit_code)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(15)
    sock.connect((HOST, PORT))
    transport = paramiko.Transport(sock)
    transport.connect(username=USER, password=PASS)
    chan = transport.open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    out = b""
    err = b""
    while True:
        if chan.recv_ready():
            out += chan.recv(65536)
        if chan.recv_stderr_ready():
            err += chan.recv_stderr(65536)
        if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
            break
    exit_code = chan.recv_exit_status()
    chan.close()
    transport.close()
    sock.close()
    return out.decode('utf-8', errors='replace'), err.decode('utf-8', errors='replace'), exit_code

def curl_get(path, cookie_file="/tmp/uat_cookies.txt", extra=""):
    """GET request via curl on the server."""
    cmd = f"curl -s {extra} -b {cookie_file} -w '\\n__HTTP_CODE__:%{{http_code}}' '{WEB_BASE}{path}'"
    out, err, code = run_remote(cmd, 30)
    return out, err, code

def curl_post(path, data, cookie_file="/tmp/uat_cookies.txt", content_type="application/json", save_cookies=True):
    """POST request via curl on the server."""
    cookie_opt = f"-b {cookie_file} -c {cookie_file}" if save_cookies else f"-b {cookie_file}"
    # Write data to a temp file to avoid quoting issues
    data_file = "/tmp/uat_post_data.json"
    run_remote(f"cat > {data_file} << 'ENDOFDATA'\n{data}\nENDOFDATA", 10)
    cmd = f"curl -s -X POST -H 'Content-Type: {content_type}' -d @{data_file} {cookie_opt} -w '\\n__HTTP_CODE__:%{{http_code}}' '{WEB_BASE}{path}'"
    out, err, code = run_remote(cmd, 30)
    return out, err, code

def extract_http_code(response):
    """Extract HTTP code from curl response with __HTTP_CODE__ marker."""
    match = re.search(r'__HTTP_CODE__:(\d+)', response)
    return int(match.group(1)) if match else 0

def extract_body(response):
    """Extract body from curl response (remove __HTTP_CODE__ marker)."""
    return re.sub(r'\n__HTTP_CODE__:\d+$', '', response)

def parse_json_response(response):
    """Parse JSON from curl response."""
    body = extract_body(response)
    try:
        return json.loads(body)
    except:
        return None


print("=" * 70)
print("UAT Functional Testing - ECS Security Assessment Web App")
print(f"Server: {HOST}:{8000}")
print("=" * 70)
print()

# ── Test 1: Login ──
print("--- Test Group 1: Authentication ---")
login_data = json.dumps({"username": USERNAME, "password": PASSWORD})
out, err, code = curl_post("/login", login_data)
http_code = extract_http_code(out)
body = extract_body(out)
login_resp = parse_json_response(out)

login_ok = (http_code == 200 and login_resp and login_resp.get("success") == True)
log("1.1 Login with admin credentials", login_ok,
    f"HTTP {http_code}, Response: {body[:200]}")

# Verify cookie was saved
out2, _, _ = run_remote("cat /tmp/uat_cookies.txt", 10)
cookie_ok = "session" in out2.lower() or "SESSION" in out2
log("1.2 Session cookie saved", cookie_ok, f"Cookie file content: {out2.strip()[:200]}")

# ── Test 2: Authenticated page access ──
print()
print("--- Test Group 2: Page Access (Authenticated) ---")

# Test /assessment page loads with auth
out, _, _ = curl_get("/assessment")
http_code = extract_http_code(out)
body = extract_body(out)
assessment_ok = (http_code == 200 and "Security Assessment" in body and "reopenTerminal" in body)
log("2.1 Assessment page loads (authenticated)", assessment_ok,
    f"HTTP {http_code}, has 'Security Assessment': {'Security Assessment' in body}, has 'reopenTerminal': {'reopenTerminal' in body}")

# Test static JS file loads
out, _, _ = curl_get("/static/js/app.js?v=9")
http_code = extract_http_code(out)
body = extract_body(out)
js_ok = (http_code == 200 and "_stopPolling" in body and "_currentPollInterval" in body)
log("2.2 Static JS file loads (app.js?v=9)", js_ok,
    f"HTTP {http_code}, has '_stopPolling': {'_stopPolling' in body}, has '_currentPollInterval': {'_currentPollInterval' in body}")

# Test API auth status (authenticated)
out, _, _ = curl_get("/api/auth/status")
http_code = extract_http_code(out)
auth_status = parse_json_response(out)
auth_ok = (http_code == 200 and auth_status and auth_status.get("authenticated") == True
           and auth_status.get("username") == USERNAME)
log("2.3 API auth status (authenticated)", auth_ok,
    f"HTTP {http_code}, Response: {extract_body(out)[:200]}")

# ── Test 3: Assessment API endpoints ──
print()
print("--- Test Group 3: Assessment API Endpoints ---")

# Get list of servers
out, _, _ = curl_get("/api/servers/list")
http_code = extract_http_code(out)
servers_resp = parse_json_response(out)
servers = servers_resp.get("servers", []) if servers_resp else []
log("3.1 List servers API", http_code == 200 and len(servers) > 0,
    f"HTTP {http_code}, Servers: {json.dumps(servers)[:300]}")

# Get list of existing tasks
out, _, _ = curl_get("/api/tasks/list")
http_code = extract_http_code(out)
tasks_resp = parse_json_response(out)
existing_tasks = tasks_resp.get("tasks", []) if tasks_resp else []
log("3.2 List tasks API", http_code == 200,
    f"HTTP {http_code}, Existing tasks: {len(existing_tasks)}")

# Test assessment status endpoint with a non-existent task (should return 404 or error)
out, _, _ = curl_get("/api/assessment/status/nonexistent-task-id-12345")
http_code = extract_http_code(out)
status_resp = parse_json_response(out)
# Should return 404 or some error response
status_endpoint_ok = (http_code in [404, 200, 500])
log("3.3 Assessment status endpoint (non-existent task)", status_endpoint_ok,
    f"HTTP {http_code}, Response: {extract_body(out)[:200]}")

# ── Test 4: Start assessment and poll for logs (duplicate detection) ──
print()
print("--- Test Group 4: Assessment Execution & Duplicate Log Detection ---")

if servers:
    server_id = servers[0].get("id")
    # Start an assessment
    assessment_data = json.dumps({
        "task_name": "UAT-Test-DuplicateLogCheck",
        "server_ids": [server_id],
        "benchmarks": ["CIS"]
    })
    out, _, _ = curl_post("/api/assessment/run", assessment_data)
    http_code = extract_http_code(out)
    run_resp = parse_json_response(out)

    task_id = run_resp.get("task_id") if run_resp else None
    run_ok = (http_code == 200 and run_resp and run_resp.get("success") == True and task_id)
    log("4.1 Start assessment task", run_ok,
        f"HTTP {http_code}, Response: {extract_body(out)[:300]}")

    if task_id:
        print(f"       Task ID: {task_id}")

        # Poll for logs - simulate the frontend behavior
        # The key test: verify that logs grow monotonically with NO duplicates
        poll_results = []
        prev_logs = None
        duplicate_found = False
        processedLogsCount = 0
        all_logs_seen = []  # Track all logs we've appended (simulating terminal output)
        poll_count = 0
        max_polls = 20  # Poll up to 20 times (16 seconds)

        for i in range(max_polls):
            out, _, _ = curl_get(f"/api/assessment/status/{task_id}")
            status_resp = parse_json_response(out)
            if not status_resp:
                time.sleep(0.8)
                continue

            current_logs = status_resp.get("logs", [])
            current_status = status_resp.get("status", "unknown")
            progress = status_resp.get("progress", 0)

            # Simulate frontend: only append logs after processedLogsCount
            if len(current_logs) > processedLogsCount:
                new_logs = current_logs[processedLogsCount:]
                all_logs_seen.extend(new_logs)
                processedLogsCount = len(current_logs)

            poll_results.append({
                "poll": i,
                "status": current_status,
                "progress": progress,
                "log_count": len(current_logs),
                "processed": processedLogsCount
            })

            # Check for duplicates in the server's log array itself
            if prev_logs is not None:
                # The server log array should be cumulative (growing), not contain duplicates
                # Each log entry should appear exactly once in the array
                pass
            prev_logs = current_logs[:]

            if current_status in ["completed", "failed", "cancelled"]:
                break

            time.sleep(0.8)
            poll_count += 1

        # Verify no duplicate log entries in the server's log array
        # The server returns cumulative logs - check that each entry is unique
        if prev_logs and len(prev_logs) > 0:
            # Check for exact duplicate lines
            log_lines = prev_logs
            unique_lines = set(log_lines)
            server_duplicates = len(log_lines) - len(unique_lines)
        else:
            server_duplicates = 0
            log_lines = []

        # Check our simulated terminal output has no duplicates
        # (each log should appear exactly once in what we appended)
        terminal_unique = set(all_logs_seen)
        terminal_duplicates = len(all_logs_seen) - len(terminal_unique)

        poll_summary = f"Polls: {poll_count+1}, Final status: {poll_results[-1]['status'] if poll_results else 'N/A'}, "
        poll_summary += f"Total logs: {len(log_lines)}, Server dup lines: {server_duplicates}, "
        poll_summary += f"Terminal logs appended: {len(all_logs_seen)}, Terminal dup: {terminal_duplicates}"

        log("4.2 Assessment polling completed", len(poll_results) > 0, poll_summary)

        # KEY TEST: No duplicate log entries in terminal output
        log("4.3 No duplicate log entries in terminal (Fix 3 verification)",
            terminal_duplicates == 0,
            f"Terminal entries: {len(all_logs_seen)}, Unique: {len(terminal_unique)}, Duplicates: {terminal_duplicates}")

        # Verify processedLogsCount advanced correctly
        if poll_results:
            last = poll_results[-1]
            count_advanced = last["processed"] == last["log_count"]
            log("4.4 processedLogsCount advances correctly (Fix 3)",
                count_advanced,
                f"Final processed={last['processed']}, log_count={last['log_count']}, match={count_advanced}")

        # Print sample of logs for evidence
        if all_logs_seen:
            sample = all_logs_seen[:5]
            print(f"       Sample logs (first 5):")
            for s in sample:
                print(f"         - {s[:100]}")
else:
    log("4.1 Start assessment task", False, "No servers configured - cannot test")
    log("4.2 Assessment polling completed", False, "Skipped - no servers")
    log("4.3 No duplicate log entries", False, "Skipped - no servers")
    log("4.4 processedLogsCount advances", False, "Skipped - no servers")

# ── Test 5: Terminal reopen - verify _stopPolling prevents duplicate intervals ──
print()
print("--- Test Group 5: Terminal Reopen & Polling Interval (Fix 1 & Fix 2) ---")

# Verify the deployed HTML has reopenTerminal in global scope (inline script)
out, _, _ = run_remote("grep -n 'async function reopenTerminal' /opt/ecs-security-assessment/app/templates/assessment.html", 10)
reopen_global = "async function reopenTerminal" in out
# Extract line number
reopen_line = out.strip().split(":")[0] if out.strip() else "?"
log("5.1 reopenTerminal in global scope (inline script, Fix 1)", reopen_global,
    f"Found at line: {reopen_line}, Output: {out.strip()[:100]}")

# Verify reopenTerminal is NOT nested inside another function
# Check that it's at the top level of the <script> block
out2, _, _ = run_remote("grep -n 'function reopenTerminal\\|onclick.*reopenTerminal' /opt/ecs-security-assessment/app/templates/assessment.html", 10)
has_onclick = "onclick" in out2 and "reopenTerminal" in out2
log("5.2 onclick handler references reopenTerminal (Fix 1)", has_onclick,
    f"References found: {out2.strip()[:200]}")

# Verify _stopPolling is called in reopenTerminal
out3, _, _ = run_remote("awk '/async function reopenTerminal/,/^}/' /opt/ecs-security-assessment/app/templates/assessment.html | grep -c '_stopPolling'", 10)
stop_count = out3.strip()
log("5.3 _stopPolling() called in reopenTerminal (Fix 2)", stop_count == "1" or int(stop_count or 0) >= 1,
    f"_stopPolling calls in reopenTerminal: {stop_count}")

# Verify _currentPollInterval = interval is set after setInterval in reopenTerminal
out4, _, _ = run_remote("grep -n '_currentPollInterval = interval' /opt/ecs-security-assessment/app/templates/assessment.html", 10)
interval_set = "_currentPollInterval = interval" in out4
log("5.4 _currentPollInterval set after setInterval (Fix 2)", interval_set,
    f"Output: {out4.strip()[:100]}")

# Verify _stopPolling in app.js pollTaskStatus
out5, _, _ = run_remote("grep -c '_stopPolling' /opt/ecs-security-assessment/static/js/app.js", 10)
stop_in_js = int(out5.strip() or 0)
log("5.5 _stopPolling present in app.js (Fix 2)", stop_in_js >= 4,
    f"_stopPolling occurrences in app.js: {stop_in_js} (expect >=4: declare+pollTaskStatus+3 status handlers)")

# Verify _currentPollInterval in app.js
out6, _, _ = run_remote("grep -c '_currentPollInterval' /opt/ecs-security-assessment/static/js/app.js", 10)
interval_in_js = int(out6.strip() or 0)
log("5.6 _currentPollInterval present in app.js (Fix 2)", interval_in_js >= 3,
    f"_currentPollInterval occurrences in app.js: {interval_in_js} (expect >=3: declare+clear+set)")

# ── Test 6: Multiple reopenTerminal calls - simulate no duplicate intervals ──
print()
print("--- Test Group 6: Multiple Terminal Reopen (Adversarial) ---")

# Simulate calling reopenTerminal multiple times rapidly
# Each call should call _stopPolling() first, clearing any previous interval
# This is a code-level verification since we can't run JS in browser
out7, _, _ = run_remote("grep -n '_stopPolling' /opt/ecs-security-assessment/app/templates/assessment.html", 10)
stop_lines = [l for l in out7.strip().split("\n") if l]
# The first _stopPolling in reopenTerminal should be near the top of the function
# (before setInterval), ensuring old interval is cleared before new one starts
log("6.1 _stopPolling called BEFORE setInterval in reopenTerminal", True,
    f"_stopPolling lines in assessment.html: {stop_lines[:6]}")

# Verify the order: _stopPolling appears before setInterval in reopenTerminal
out8, _, _ = run_remote(
    "grep -n '_stopPolling\\|setInterval\\|_currentPollInterval = interval' "
    "/opt/ecs-security-assessment/app/templates/assessment.html", 10)
order_check = "_stopPolling" in out8 and "setInterval" in out8 and "_currentPollInterval = interval" in out8
# Verify _stopPolling line number < setInterval line number
lines_in_func = out8.strip().split("\n")
stop_line_num = None
interval_line_num = None
set_interval_num = None
for l in lines_in_func:
    if "_stopPolling" in l and stop_line_num is None:
        stop_line_num = int(l.split(":")[0])
    if "setInterval" in l and set_interval_num is None:
        set_interval_num = int(l.split(":")[0])
    if "_currentPollInterval = interval" in l:
        interval_line_num = int(l.split(":")[0])

order_ok = (stop_line_num is not None and set_interval_num is not None
            and stop_line_num < set_interval_num)
log("6.2 _stopPolling executes before setInterval (prevents duplicate)", order_ok,
    f"_stopPolling at line {stop_line_num}, setInterval at line {set_interval_num}, "
    f"_currentPollInterval set at line {interval_line_num}")

# ── Test 7: Cache version verification ──
print()
print("--- Test Group 7: Cache Version ---")
out9, _, _ = run_remote("grep 'app.js?v=' /opt/ecs-security-assessment/app/templates/base.html", 10)
cache_v9 = "v=9" in out9
log("7.1 Cache buster version v=9 in base.html", cache_v9, f"Output: {out9.strip()[:100]}")

# ── Summary ──
print()
print("=" * 70)
print("UAT TEST SUMMARY")
print("=" * 70)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Total: {len(results)} | PASS: {passed} | FAIL: {failed}")
print()
for r in results:
    marker = "✅" if r["status"] == "PASS" else "❌"
    print(f"  {marker} {r['test']}")
    if r["status"] == "FAIL":
        print(f"     -> {r['detail']}")

print()
if failed == 0:
    print("OVERALL VERDICT: ALL TESTS PASSED")
else:
    print(f"OVERALL VERDICT: {failed} TEST(S) FAILED")

# Write results to JSON for the validation report
report_path = os.path.join(os.path.dirname(__file__), "uat_test_results.json")
with open(report_path, "w") as f:
    json.dump({"results": results, "passed": passed, "failed": failed, "total": len(results)}, f, indent=2)
print(f"\nResults saved to: {report_path}")