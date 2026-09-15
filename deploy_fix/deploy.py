import base64
import subprocess
import os
import sys

SSH_HELPER = r'N:\codearts\ssh_helper.py'
LOCAL_DIR = r'N:\codearts\deploy_fix'
REMOTE_DIR = '/opt/ecs-security-assessment/app/templates'

FILES = [
    'login.html',
    'register.html',
    'account.html',
    'audit_log.html',
    'regcodes.html',
    'assessment.html',
]

def run_ssh(cmd, timeout=60):
    """Run a command via the SSH helper."""
    result = subprocess.run(
        ['python', SSH_HELPER, cmd, str(timeout)],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr, result.returncode

def deploy_file(filename):
    """Deploy a single file via base64 encoding."""
    local_path = os.path.join(LOCAL_DIR, filename)
    remote_path = f"{REMOTE_DIR}/{filename}"

    print(f"\n=== Deploying {filename} ===")

    with open(local_path, 'rb') as f:
        content = f.read()

    b64 = base64.b64encode(content).decode()
    print(f"  File size: {len(content)} bytes, base64 length: {len(b64)}")

    # Clear the temp file on server
    stdout, stderr, rc = run_ssh('rm -f /tmp/deploy_b64.txt')
    if rc != 0:
        print(f"  WARN: rm temp file rc={rc}")

    # Send base64 in chunks
    chunk_size = 5000
    chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
    print(f"  Sending {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        op = '>' if i == 0 else '>>'
        # Use printf to avoid echo interpretation issues
        cmd = f'printf "%s" "{chunk}" {op} /tmp/deploy_b64.txt'
        stdout, stderr, rc = run_ssh(cmd, 30)
        if rc != 0:
            print(f"  ERROR: chunk {i+1}/{len(chunks)} failed! rc={rc}")
            print(f"  stderr: {stderr}")
            return False
        if (i + 1) % 10 == 0 or i == len(chunks) - 1:
            print(f"  Sent chunk {i+1}/{len(chunks)}")

    # Verify base64 length on server
    stdout, stderr, rc = run_ssh('wc -c < /tmp/deploy_b64.txt')
    # Extract first line (SSH helper appends EXIT_CODE line)
    server_b64_len = stdout.strip().split('\n')[0].strip()
    print(f"  Server base64 length: {server_b64_len} (expected: {len(b64)})")
    if str(server_b64_len) != str(len(b64)):
        print(f"  ERROR: base64 length mismatch!")
        return False

    # Backup original file
    stdout, stderr, rc = run_ssh(f'cp {remote_path} {remote_path}.bak_fix')
    if rc != 0:
        print(f"  WARN: backup failed rc={rc}")

    # Decode base64 to target file
    stdout, stderr, rc = run_ssh(f'base64 -d /tmp/deploy_b64.txt > {remote_path}')
    if rc != 0:
        print(f"  ERROR: decode failed! rc={rc}")
        print(f"  stderr: {stderr}")
        return False

    # Verify file size on server
    stdout, stderr, rc = run_ssh(f'wc -c < {remote_path}')
    server_file_size = stdout.strip().split('\n')[0].strip()
    print(f"  Server file size: {server_file_size} bytes (expected: {len(content)})")
    if str(server_file_size) != str(len(content)):
        print(f"  ERROR: file size mismatch!")
        return False

    print(f"  SUCCESS: {filename} deployed!")
    return True

def main():
    print("Starting deployment of fixed HTML templates...")

    results = {}
    for filename in FILES:
        success = deploy_file(filename)
        results[filename] = success

    # Clean up temp file
    run_ssh('rm -f /tmp/deploy_b64.txt')

    print("\n=== Deployment Summary ===")
    all_ok = True
    for filename, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {filename}: {status}")
        if not success:
            all_ok = False

    if all_ok:
        print("\nAll files deployed successfully!")
        sys.exit(0)
    else:
        print("\nSome files failed to deploy!")
        sys.exit(1)

if __name__ == '__main__':
    main()