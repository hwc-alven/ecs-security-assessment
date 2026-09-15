"""Add Google Fonts to login.html and register.html on server."""
import subprocess
import sys

SSH_HELPER = r'N:\codearts\ssh_helper.py'

def run_ssh(cmd, timeout='30'):
    result = subprocess.run(
        ['python', SSH_HELPER, cmd, timeout],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.returncode, result.stdout, result.stderr

# Create a script on the server that adds fonts to login.html and register.html
script_cmd = """python3 -c "
import re

fonts = '''    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap\" rel=\"stylesheet\">'''

for fpath in ['/opt/ecs-security-assessment/app/templates/login.html', '/opt/ecs-security-assessment/app/templates/register.html']:
    with open(fpath, 'r') as f:
        content = f.read()
    if 'fonts.googleapis.com' not in content:
        content = content.replace('<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">', '<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\\n' + fonts)
        with open(fpath, 'w') as f:
            f.write(content)
        print(f'Added fonts to {fpath}')
    else:
        print(f'Fonts already in {fpath}')
" && echo SCRIPT_DONE"""

rc, out, err = run_ssh(script_cmd, '15')
print(f'Result: {out.strip()}')
print(f'Stderr: {err.strip()}')

# Verify
rc, out, err = run_ssh('grep -c "fonts.googleapis" /opt/ecs-security-assessment/app/templates/login.html', '10')
print(f'login.html fonts count: {out.strip()}')

rc, out, err = run_ssh('grep -c "fonts.googleapis" /opt/ecs-security-assessment/app/templates/register.html', '10')
print(f'register.html fonts count: {out.strip()}')

# Test login page now has fonts
rc, out, err = run_ssh('curl -s http://localhost:8000/login | grep -c "Inter"', '10')
print(f'Inter in login page: {out.strip()}')

rc, out, err = run_ssh('curl -s http://localhost:8000/register | grep -c "Inter"', '10')
print(f'Inter in register page: {out.strip()}')