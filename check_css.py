import subprocess, os

ENV = {**os.environ, 'SSH_ASKPASS': r'N:\codearts\askpass.cmd', 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': 'none'}
SSH = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 'root@119.8.181.202']

# Check CSS file size and first/last lines
r = subprocess.run(SSH + ['wc -l /opt/ecs-security-assessment/static/css/style.css && wc -c /opt/ecs-security-assessment/static/css/style.css'], capture_output=True, timeout=15, env=ENV)
print('CSS file size:', r.stdout.decode().strip())

# Show navbar-related CSS
r = subprocess.run(SSH + ['grep -n "nav\\|navbar" /opt/ecs-security-assessment/static/css/style.css'], capture_output=True, timeout=15, env=ENV)
print('---CSS navbar lines---')
print(r.stdout.decode()[:3000])