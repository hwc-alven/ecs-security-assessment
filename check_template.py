import subprocess, os

ENV = {**os.environ, 'SSH_ASKPASS': r'N:\codearts\askpass.cmd', 'SSH_ASKPASS_REQUIRE': 'force', 'DISPLAY': 'none'}
SSH = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 'root@119.8.181.202']

def ssh_cmd(cmd):
    r = subprocess.run(SSH + [cmd], capture_output=True, timeout=15, env=ENV)
    return r.stdout.decode().strip()

# Show all lines with "th>ID" in the template
print('=== All th>ID lines in template ===')
out = ssh_cmd('grep -n "th>ID" /opt/ecs-security-assessment/app/templates/assessment.html')
print(out)

# Show lines around the task history section
print()
print('=== Task history section (lines 220-280) ===')
out = ssh_cmd('sed -n "220,280p" /opt/ecs-security-assessment/app/templates/assessment.html')
print(out)