import subprocess, os

ENV = {**os.environ, 'SSH_ASKPASS': r'N:\codearts\askpass.cmd', 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': 'none'}
SSH = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 'root@119.8.181.202']

def ssh_cmd(cmd):
    r = subprocess.run(SSH + [cmd], capture_output=True, timeout=15, env=ENV)
    return r.stdout.decode().strip()

# Check the exact header line in the template
print('=== Template header line ===')
print(ssh_cmd('grep "th>ID" /opt/ecs-security-assessment/app/templates/assessment.html'))

# Check the rendered page header
ssh_cmd("curl -s -c /tmp/admin_cookies.txt -X POST http://localhost:8000/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Test123!@#\"}'")
print()
print('=== Rendered page header ===')
print(ssh_cmd('curl -s -b /tmp/admin_cookies.txt http://localhost:8000/assessment | grep "th>ID"'))

# Clear Jinja2 cache and restart
print()
print('=== Clear cache and restart ===')
print(ssh_cmd('find /opt/ecs-security-assessment -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; echo done'))
print(ssh_cmd('systemctl restart ecs-security-assessment && sleep 3 && systemctl is-active ecs-security-assessment'))

# Re-check
ssh_cmd("curl -s -c /tmp/admin_cookies.txt -X POST http://localhost:8000/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"Test123!@#\"}'")
print()
print('=== After cache clear - rendered header ===')
print(ssh_cmd('curl -s -b /tmp/admin_cookies.txt http://localhost:8000/assessment | grep "th>ID"'))
print()
print('=== After cache clear - Live Terminal count ===')
print(ssh_cmd('curl -s -b /tmp/admin_cookies.txt http://localhost:8000/assessment | grep -c "Live Terminal"'))
print('reopenTerminal count:', ssh_cmd('curl -s -b /tmp/admin_cookies.txt http://localhost:8000/assessment | grep -c "reopenTerminal"'))