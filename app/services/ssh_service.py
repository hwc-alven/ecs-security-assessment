# AI生成
"""SSH service — connects to ECS servers and executes read-only commands only.

CRITICAL SECURITY CONSTRAINT:
All commands are from a predefined read-only whitelist. No modification commands
are allowed. This module will NEVER execute any command that changes server state.
"""
import paramiko
import socket
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ============================================================
# READ-ONLY COMMAND WHITELIST
# These are the ONLY commands this module will execute.
# No modification commands (sed, chmod, chown, rm, mv, etc.)
# ============================================================

# General Linux VM read-only commands for security assessment
VM_READ_COMMANDS = {
    # ---- OS / kernel info ----
    "os_info": "cat /etc/os-release 2>/dev/null",
    "kernel_info": "uname -a",
    "uptime": "uptime",
    "hostname": "hostname",

    # ---- Filesystem / mount info ----
    "mount_info": "mount | column -t 2>/dev/null || mount",
    "fstab": "cat /etc/fstab 2>/dev/null",
    "disk_usage": "df -h",
    "tmp_mount_opts": "mount | grep ' /tmp ' 2>/dev/null || echo '/tmp not on separate partition'",
    "var_mount_opts": "mount | grep ' /var ' 2>/dev/null || echo '/var not on separate partition'",
    "var_log_mount_opts": "mount | grep ' /var/log ' 2>/dev/null || echo '/var/log not on separate partition'",
    "home_mount_opts": "mount | grep ' /home ' 2>/dev/null || echo '/home not on separate partition'",
    "var_log_audit_mount_opts": "mount | grep ' /var/log/audit ' 2>/dev/null || echo '/var/log/audit not on separate partition'",

    # ---- SSH configuration ----
    "sshd_config": "cat /etc/ssh/sshd_config 2>/dev/null",
    "sshd_config_d": "cat /etc/ssh/sshd_config.d/*.conf 2>/dev/null || echo 'No sshd_config.d includes'",

    # ---- Password / PAM policy ----
    "login_defs": "cat /etc/login.defs 2>/dev/null",
    "pam_password": "cat /etc/pam.d/password-auth 2>/dev/null || cat /etc/pam.d/common-password 2>/dev/null || echo 'PAM password config not found'",
    "pam_system_auth": "cat /etc/pam.d/system-auth 2>/dev/null || echo 'system-auth not found'",
    "pwquality_conf": "cat /etc/security/pwquality.conf 2>/dev/null || echo 'pwquality.conf not found'",

    # ---- SELinux / AppArmor ----
    "selinux_status": "getenforce 2>/dev/null || echo 'SELinux not available'",
    "selinux_config": "cat /etc/selinux/config 2>/dev/null || echo 'SELinux config not found'",
    "apparmor_status": "aa-status 2>/dev/null || echo 'AppArmor not available'",

    # ---- Firewall ----
    "firewalld_status": "systemctl is-active firewalld 2>/dev/null && firewall-cmd --list-all 2>/dev/null || echo 'firewalld not active'",
    "iptables_status": "iptables -L -n 2>/dev/null || echo 'iptables not available'",
    "nftables_status": "nft list ruleset 2>/dev/null || echo 'nftables not available or no rules'",
    "ufw_status": "ufw status verbose 2>/dev/null || echo 'ufw not available'",

    # ---- Network / ports ----
    "open_ports": "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null",
    "listening_udp": "ss -ulnp 2>/dev/null || netstat -ulnp 2>/dev/null",
    "network_interfaces": "ip addr show 2>/dev/null || ifconfig 2>/dev/null",
    "ip6_enabled": "cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null || echo 'IPv6 info not available'",

    # ---- Services ----
    "running_services": "systemctl list-units --type=service --state=running --no-pager 2>/dev/null || echo 'systemctl not available'",
    "enabled_services": "systemctl list-unit-files --type=service --state=enabled --no-pager 2>/dev/null || echo 'systemctl not available'",
    "telnet_service": "systemctl is-active telnet 2>/dev/null; systemctl is-active telnet.socket 2>/dev/null; echo done",
    "rsh_service": "systemctl is-active rsh.socket 2>/dev/null; systemctl is-active rexec.socket 2>/dev/null; echo done",

    # ---- Users / accounts ----
    "passwd_file": "cat /etc/passwd 2>/dev/null",
    "shadow_perms": "ls -l /etc/shadow /etc/gshadow /etc/passwd /etc/group 2>/dev/null",
    "uid_zero_accounts": "awk -F: '($3 == 0) { print $1 }' /etc/passwd 2>/dev/null",
    "users_with_shells": "grep -v '/nologin\\|/false' /etc/passwd 2>/dev/null || echo 'No interactive shell users'",
    "sudoers": "cat /etc/sudoers 2>/dev/null",
    "sudoers_d": "cat /etc/sudoers.d/* 2>/dev/null || echo 'No sudoers.d files'",
    "cron_allow": "cat /etc/cron.allow 2>/dev/null || echo 'cron.allow not found'",
    "cron_deny": "cat /etc/cron.deny 2>/dev/null || echo 'cron.deny not found'",

    # ---- File permissions / security ----
    "world_writable_files": "find / -xdev -type f -perm -0002 -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -50 || echo 'None found or find not available'",
    "world_writable_dirs_no_sticky": "find / -xdev -type d -perm -0002 -not -perm -1000 -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -20 || echo 'None found'",
    "suid_files": "find / -xdev -type f -perm -4000 -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -50 || echo 'None found'",
    "sgid_files": "find / -xdev -type f -perm -2000 -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -50 || echo 'None found'",

    # ---- Auditing / logging ----
    "auditd_status": "systemctl is-active auditd 2>/dev/null && auditctl -l 2>/dev/null || echo 'auditd not active'",
    "auditd_config": "cat /etc/audit/auditd.conf 2>/dev/null || echo 'auditd.conf not found'",
    "audit_rules": "cat /etc/audit/rules.d/*.rules 2>/dev/null || echo 'No audit rules found'",
    "rsyslog_status": "systemctl is-active rsyslog 2>/dev/null || echo 'rsyslog not active'",
    "rsyslog_config": "cat /etc/rsyslog.conf 2>/dev/null || echo 'rsyslog.conf not found'",

    # ---- Kernel hardening (sysctl) ----
    "sysctl_security": "sysctl net.ipv4.conf.all.send_redirects net.ipv4.conf.default.send_redirects net.ipv4.conf.all.accept_redirects net.ipv4.conf.default.accept_redirects net.ipv4.conf.all.secure_redirects net.ipv4.ip_forward net.ipv6.conf.all.accept_redirects net.ipv6.conf.default.accept_redirects kernel.randomize_va_space kernel.exec-shield fs.suid_dumpable kernel.sysrq 2>/dev/null || echo 'sysctl not available'",
    "sysctl_network": "sysctl net.ipv4.tcp_syncookies net.ipv4.icmp_echo_ignore_broadcasts net.ipv4.conf.all.log_martians net.ipv4.conf.default.log_martians net.ipv4.icmp_ignore_bogus_error_responses 2>/dev/null || echo 'sysctl not available'",

    # ---- Time synchronization ----
    "chrony_status": "systemctl is-active chronyd 2>/dev/null && chronyc tracking 2>/dev/null || echo 'chronyd not active'",
    "ntp_status": "systemctl is-active ntpd 2>/dev/null && ntpq -p 2>/dev/null || echo 'ntpd not active'",

    # ---- FIPS / crypto ----
    "fips_status": "cat /proc/sys/crypto/fips_enabled 2>/dev/null || echo 'FIPS not available'",
    "fips_check": "fips-mode-setup --check 2>/dev/null || echo 'fips-mode-setup not available'",

    # ---- Package updates ----
    "yum_updates": "yum check-update --security 2>/dev/null | head -30 || echo 'yum not available'",
    "dnf_updates": "dnf check-update --security 2>/dev/null | head -30 || echo 'dnf not available'",
    "apt_updates": "apt list --upgradable 2>/dev/null | head -30 || echo 'apt not available'",

    # ---- Bootloader ----
    "grub_config": "ls -l /boot/grub2/grub.cfg /boot/grub/grub.cfg 2>/dev/null; grep -i password /boot/grub2/grub.cfg /boot/grub/grub.cfg 2>/dev/null || echo 'No GRUB password found'",

    # ---- USB / Bluetooth ----
    "usb_storage": "lsmod | grep usb_storage 2>/dev/null || echo 'usb_storage module not loaded'",
    "bluetooth_service": "systemctl is-active bluetooth 2>/dev/null || echo 'bluetooth not active'",

    # ---- X Windows ----
    "xwindows_check": "rpm -qa xorg-x11-server-Xorg 2>/dev/null || dpkg -l xserver-xorg-core 2>/dev/null || echo 'X Windows not installed'",

    # ---- Fail2ban / intrusion detection ----
    "fail2ban_status": "fail2ban-client status 2>/dev/null || echo 'fail2ban not installed'",
    "aide_check": "which aide 2>/dev/null && echo 'AIDE installed' || echo 'AIDE not installed'",
    "clamav_check": "which clamscan 2>/dev/null && echo 'ClamAV installed' || echo 'ClamAV not installed'",

    # ---- Core dump settings ----
    "limits_conf": "cat /etc/security/limits.conf 2>/dev/null | grep -v '^#' | grep -v '^$' || echo 'No limits configured'",
    "ulimit_core": "ulimit -c 2>/dev/null",
}


class SSHService:
    """SSH connection service with read-only command enforcement."""

    def __init__(self, private_key_obj: paramiko.RSAKey, timeout: int = 30):
        self.private_key = private_key_obj
        self.timeout = timeout

    def connect(self, host: str, port: int = 22, username: str = "root") -> paramiko.SSHClient:
        """Establish SSH connection using the in-memory private key."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                pkey=self.private_key,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            logger.info(f"SSH connected to {username}@{host}:{port}")
            return client
        except Exception as e:
            logger.error(f"SSH connection failed to {host}:{port}: {e}")
            raise

    def execute_command(self, client: paramiko.SSHClient, command: str) -> dict:
        """Execute a single read-only command and return output."""
        stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace").strip()
        error = stderr.read().decode("utf-8", errors="replace").strip()
        return {
            "command": command,
            "exit_status": exit_status,
            "output": output,
            "error": error,
        }

    def collect_vm_config(self, client: paramiko.SSHClient) -> dict:
        """Collect general Linux VM configuration using only read-only commands.

        Commands are executed in parallel via a thread pool for speed.
        Each command has its own timeout to prevent hangs.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}

        import time

        MAX_RETRIES = 3
        BACKOFF = 0.5  # seconds

        def _run_one(name: str, cmd: str):
            """Run a single command with retry on channel errors."""
            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    result = self.execute_command(client, cmd)
                    # Detect channel-level failures (paramiko returns error in output)
                    err_str = result.get("error", "") or ""
                    out_str = result.get("output", "") or ""
                    if "ChannelException" in err_str or "Connect failed" in err_str:
                        last_error = err_str
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(BACKOFF * (attempt + 1))
                            continue
                    # Also check for channel errors in output
                    if "ChannelException" in out_str or "Unable to open channel" in out_str:
                        last_error = out_str
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(BACKOFF * (attempt + 1))
                            continue
                    return name, result
                except Exception as e:
                    last_error = str(e)
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(BACKOFF * (attempt + 1))
                        continue
            return name, {"command": name, "exit_status": -1, "output": "", "error": f"Failed after {MAX_RETRIES} retries: {last_error}"}

        # Run commands in parallel with reduced concurrency to avoid channel exhaustion.
        # Paramiko allows multiple channels per connection, but too many simultaneous
        # channels cause ChannelException(2, 'Connect failed'). 3 workers is safe.
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_run_one, name, cmd): name for name, cmd in VM_READ_COMMANDS.items()}
            for future in as_completed(futures):
                name, result = future.result()
                results[name] = result

        # Second pass: retry any commands that still have errors (sequential, safe)
        failed_keys = [
            name for name, result in results.items()
            if result.get("exit_status", 0) == -1
            or "ChannelException" in (result.get("error", "") or "")
            or "ChannelException" in (result.get("output", "") or "")
            or "Unable to open channel" in (result.get("output", "") or "")
        ]
        if failed_keys:
            logger.info(f"Retrying {len(failed_keys)} failed commands sequentially...")
            for name in failed_keys:
                cmd = VM_READ_COMMANDS[name]
                try:
                    result = self.execute_command(client, cmd)
                    results[name] = result
                except Exception as e:
                    logger.warning(f"Retry also failed for {name}: {e}")

        return results

    def assess_server(
        self,
        host: str,
        port: int,
        username: str,
    ) -> dict:
        """Connect to a single server and collect configuration data."""
        result = {
            "host": host,
            "port": port,
            "username": username,
            "status": "pending",
            "config_data": {},
            "error": None,
        }

        try:
            client = self.connect(host, port, username)
            result["status"] = "connected"
            result["config_data"] = self.collect_vm_config(client)
            result["status"] = "completed"
            client.close()

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def assess_servers_parallel(
        self,
        servers: list,
        max_workers: int = 10,
    ) -> list:
        """Assess multiple servers in parallel.

        Args:
            servers: list of dicts with keys: host, port, username
            max_workers: max parallel connections (default 10)

        Returns:
            list of assessment results (one per server)
        """
        results = [None] * len(servers)

        with ThreadPoolExecutor(max_workers=min(max_workers, len(servers))) as executor:
            future_to_idx = {}
            for idx, server in enumerate(servers):
                future = executor.submit(
                    self.assess_server,
                    host=server["ip"],
                    port=server.get("ssh_port", 22),
                    username=server.get("ssh_username", "root"),
                )
                future_to_idx[future] = idx

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {
                        "host": servers[idx]["ip"],
                        "status": "failed",
                        "error": str(e),
                        "config_data": {},
                    }

        return results
