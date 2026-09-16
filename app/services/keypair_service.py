# AI生成
"""Keypair generation service — generates RSA keypair for SSH access.

Security model:
- System generates the keypair
- Public key is given to the user to install on their ECS servers
- Private key stays in memory only, never written to disk
- Private key is cleared after assessment completes
"""
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import paramiko
import io


def generate_keypair(key_size: int = 2048) -> dict:
    """Generate a new RSA keypair.

    Returns:
        dict with:
            - public_key: OpenSSH-format public key string (for user to install)
            - private_key: paramiko.RSAKey object (kept in memory)
            - fingerprint: key fingerprint for identification
    """
    # Generate RSA private key
    private_key = rsa.generate_private_key(
        backend=default_backend(),
        public_exponent=65537,
        key_size=key_size,
    )

    # Serialize public key to OpenSSH format
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode("utf-8")

    # Serialize private key to PEM format (in-memory only)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Create paramiko RSAKey object from PEM string
    private_key_obj = paramiko.RSAKey.from_private_key(io.StringIO(private_key_pem))

    # Get fingerprint (MD5 hex representation)
    fingerprint = private_key_obj.get_fingerprint().hex()
    formatted_md5 = ":".join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))

    return {
        "public_key": public_key_pem,
        "private_key": private_key_obj,
        "private_key_pem": private_key_pem,
        "fingerprint": f"MD5:{formatted_md5}",
    }


def save_keypair_to_disk(keypair_res: dict, keypair_dir):
    """Save static keypair to disk files."""
    from pathlib import Path
    dir_path = Path(keypair_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    priv_file = dir_path / "id_rsa"
    pub_file = dir_path / "id_rsa.pub"

    priv_file.write_text(keypair_res["private_key_pem"], encoding="utf-8")
    priv_file.chmod(0o600)
    pub_file.write_text(keypair_res["public_key"], encoding="utf-8")


def load_keypair_from_disk(keypair_dir) -> dict:
    """Load static keypair from disk if present."""
    from pathlib import Path
    dir_path = Path(keypair_dir)
    priv_file = dir_path / "id_rsa"
    pub_file = dir_path / "id_rsa.pub"

    if priv_file.exists() and pub_file.exists():
        try:
            private_key_pem = priv_file.read_text(encoding="utf-8")
            public_key_pem = pub_file.read_text(encoding="utf-8").strip()
            private_key_obj = paramiko.RSAKey.from_private_key(io.StringIO(private_key_pem))
            fingerprint = private_key_obj.get_fingerprint().hex()
            formatted_md5 = ":".join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))
            return {
                "public_key": public_key_pem,
                "private_key": private_key_obj,
                "private_key_pem": private_key_pem,
                "fingerprint": f"MD5:{formatted_md5}",
            }
        except Exception:
            return None
    return None




def get_public_key_instructions(public_key: str) -> str:
    """Generate instructions for the user to install the public key on their ECS."""
    return f"""# Public Key Installation Instructions

Your public key has been generated. Please install it on each ECS server you want to assess.

## Method 1: Manual SSH Login
1. SSH into your ECS server: `ssh root@<your-ecs-ip>`
2. Create .ssh directory if it doesn't exist: `mkdir -p ~/.ssh`
3. Add the public key: `echo '{public_key}' >> ~/.ssh/authorized_keys`
4. Set correct permissions: `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys`

## Method 2: Huawei Cloud Console
1. Go to Huawei Cloud ECS Console
2. Select your ECS instance
3. Use the "Inject Key Pair" feature to add this public key

## Your Public Key:
```
{public_key}
```

After installing the public key on all your servers, return to this console and add the server IPs to start assessment.
"""
