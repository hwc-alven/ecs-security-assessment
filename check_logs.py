import subprocess, os

ENV = {**os.environ, 'SSH_ASKPASS': r'N:\codearts\askpass.cmd', 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': 'none'}
SSH = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 'root@119.8.181.202']

# Check recent service logs for errors
r = subprocess.run(SSH + ['journalctl -u ecs-security-assessment --since "1 min ago" --no-pager 2>&1 | tail -20'], capture_output=True, timeout=15, env=ENV)
print('---Recent logs---')
print(r.stdout.decode()[:2000])

# Check that the CSS version query param matches
r = subprocess.run(SSH + ['grep "style.css" /opt/ecs-security-assessment/app/templates/base.html'], capture_output=True, timeout=15, env=ENV)
print('CSS version in base.html:', r.stdout.decode().strip())