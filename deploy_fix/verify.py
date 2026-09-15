import paramiko
import socket
import json

HOST = "119.8.181.202"
USER = "root"
PASS = "Test123!@#"
PORT = 22

def run_remote(cmd, timeout=30):
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

# Step 1: Write login JSON to server
print("=== Writing login JSON ===")
login_json = json.dumps({"username": "admin", "password": "Test123!@#"})
# Use base64 to write the JSON file safely
import base64
b64 = base64.b64encode(login_json.encode()).decode()
out, err, rc = run_remote(f'echo -n "{b64}" | base64 -d > /tmp/login.json')
print(f"Write login.json: rc={rc}")

# Step 2: Login and get cookie
print("\n=== Logging in as admin ===")
out, err, rc = run_remote(
    'curl -s -c /tmp/cookies.txt -X POST http://localhost:8000/login '
    '-H "Content-Type: application/json" -d @/tmp/login.json', 30
)
print(f"Login response: {out.strip()}")
print(f"Login rc={rc}")

# Step 3: Test authenticated pages
print("\n=== Testing authenticated pages ===")
pages = ['/assessment', '/account', '/audit-log', '/regcodes', '/']
for page in pages:
    out, err, rc = run_remote(
        f'curl -s -o /dev/null -w "%{{http_code}}" -b /tmp/cookies.txt http://localhost:8000{page}', 30
    )
    status = out.strip().split('\n')[0].strip()
    print(f"  {page}: HTTP {status}")

# Step 4: Test unauthenticated pages
print("\n=== Testing unauthenticated pages ===")
for page in ['/login', '/register']:
    out, err, rc = run_remote(
        f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:8000{page}', 30
    )
    status = out.strip().split('\n')[0].strip()
    print(f"  {page}: HTTP {status}")

# Step 5: Check for remaining light theme colors in all template files
print("\n=== Checking for remaining light theme colors ===")
templates = ['login.html', 'register.html', 'account.html', 'audit_log.html', 'regcodes.html', 'assessment.html', 'base.html']
light_patterns = r'background: white\|background: #fff\b\|color: #1a237e\|color: #37474f\|border.*#e0e0e0\|background: #ffebee\|background: #f5f5f5\|color: #9e9e9e\|color: #78909c\|border: 1px solid #ccc\|background: #c8e6c9\|background: #ffcdd2\|background: #eceff1\|background: #fff3e0\|color: #616161\|background: #f8f9fa\|background: #fff8e1\|color: #666\b\|color: #555\b\|background: #e3f2fd'

for tmpl in templates:
    out, err, rc = run_remote(
        f'grep -c "{light_patterns}" /opt/ecs-security-assessment/app/templates/{tmpl}', 15
    )
    count = out.strip().split('\n')[0].strip() if out.strip() else '0'
    # grep returns exit code 1 when no matches found
    if rc == 1:
        count = '0'
    status = "CLEAN" if count == '0' else f"FOUND {count} matches"
    print(f"  {tmpl}: {status}")

# Step 6: Verify dark theme colors are present
print("\n=== Verifying dark theme colors present ===")
for tmpl in ['login.html', 'register.html']:
    out, err, rc = run_remote(
        f'grep -c "#0A0A0A\|#EDEDEF\|#6366F1" /opt/ecs-security-assessment/app/templates/{tmpl}', 15
    )
    count = out.strip().split('\n')[0].strip() if out.strip() else '0'
    print(f"  {tmpl}: {count} dark theme color references")

# Cleanup
run_remote('rm -f /tmp/login.json /tmp/cookies.txt')

print("\n=== Verification Complete ===")