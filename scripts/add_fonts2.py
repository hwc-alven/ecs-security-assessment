"""Add Google Fonts to login.html and register.html on server via base64 script."""
import base64
import subprocess
import sys

SSH_HELPER = r'N:\codearts\ssh_helper.py'

def run_ssh(cmd, timeout='30'):
    result = subprocess.run(
        ['python', SSH_HELPER, cmd, timeout],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.returncode, result.stdout, result.stderr

# Python script to run on server
server_script = '''import re

fonts_line = '    <link rel="preconnect" href="https://fonts.googleapis.com">'
fonts_full = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">"""

viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

for fpath in ['/opt/ecs-security-assessment/app/templates/login.html', '/opt/ecs-security-assessment/app/templates/register.html']:
    with open(fpath, 'r') as f:
        content = f.read()
    if 'fonts.googleapis.com' not in content:
        content = content.replace(viewport, viewport + '\\n' + fonts_full)
        with open(fpath, 'w') as f:
            f.write(content)
        print('Added fonts to ' + fpath)
    else:
        print('Fonts already in ' + fpath)
'''

# Base64 encode the script
b64 = base64.b64encode(server_script.encode('utf-8')).decode('ascii')

# Deploy and run the script
chunk_size = 4000
chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
print(f'Script base64: {len(b64)} bytes, {len(chunks)} chunks')

# Write chunks to temp file
rc, out, err = run_ssh('echo -n "" > /tmp/font_script_b64.py', '10')
for i, chunk in enumerate(chunks):
    cmd = f'echo -n "{chunk}" >> /tmp/font_script_b64.py'
    rc, out, err = run_ssh(cmd, '15')
    if rc != 0:
        print(f'Chunk {i+1} failed: {err}')
        sys.exit(1)

# Decode and run
rc, out, err = run_ssh('base64 -d /tmp/font_script_b64.py > /tmp/font_script.py && python3 /tmp/font_script.py && echo SCRIPT_OK', '15')
print(f'Script result: {out.strip()}')
print(f'Stderr: {err.strip()}')

# Verify
print('\n=== Verification ===')
rc, out, err = run_ssh('grep -c "fonts.googleapis" /opt/ecs-security-assessment/app/templates/login.html', '10')
print(f'login.html fonts count: {out.strip()}')

rc, out, err = run_ssh('grep -c "fonts.googleapis" /opt/ecs-security-assessment/app/templates/register.html', '10')
print(f'register.html fonts count: {out.strip()}')

# Test login page
rc, out, err = run_ssh('curl -s http://localhost:8000/login | grep -c "Inter"', '10')
print(f'Inter in login page HTML: {out.strip()}')

rc, out, err = run_ssh('curl -s http://localhost:8000/register | grep -c "Inter"', '10')
print(f'Inter in register page HTML: {out.strip()}')

# Full HTTP status check
print('\n=== Full HTTP Status Check ===')
rc, out, err = run_ssh('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login', '10')
print(f'/login: {out.strip()}')

rc, out, err = run_ssh('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/register', '10')
print(f'/register: {out.strip()}')

rc, out, err = run_ssh('curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/static/css/style.css?v=10"', '10')
print(f'/static/css/style.css?v=10: {out.strip()}')

print('\n=== DONE ===')