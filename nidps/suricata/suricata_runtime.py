"""
suricata_runtime.py

Runtime helpers for managing Suricata IPS and NFQUEUE rules.

Responsibilities:
- Ensure NFQUEUE iptables rules exist
- Start/stop Suricata via systemd
- Check whether the Suricata service is active
"""

from __future__ import annotations

import subprocess


SERVICE_NAME = "suricata"
SYSTEMCTL = ["sudo", "systemctl"]


def _run_quiet(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )


def ensure_nfqueue_rules() -> None:
    """
    Ensure NFQUEUE rules exist in INPUT and OUTPUT chains.
    Uses iptables -C to check before inserting.
    """

    checks_and_adds = [
        (
            ["sudo", "iptables", "-C", "INPUT", "-j", "NFQUEUE", "--queue-num", "0"],
            ["sudo", "iptables", "-I", "INPUT", "-j", "NFQUEUE", "--queue-num", "0"],
        ),
        (
            ["sudo", "iptables", "-C", "FORWARD", "-j", "NFQUEUE", "--queue-num", "0"],
            ["sudo", "iptables", "-I", "FORWARD", "-j", "NFQUEUE", "--queue-num", "0"],
        ),
        (
            ["sudo", "iptables", "-C", "OUTPUT", "-j", "NFQUEUE", "--queue-num", "0"],
            ["sudo", "iptables", "-I", "OUTPUT", "-j", "NFQUEUE", "--queue-num", "0"],
        ),
    ]

    for check_cmd, add_cmd in checks_and_adds:
        result = _run_quiet(check_cmd)
        if result.returncode != 0:
            subprocess.run(add_cmd, check=True)


def is_suricata_ips_running() -> bool:
    """Returns True if the Suricata systemd service is active."""

    try:
        result = subprocess.run(
            SYSTEMCTL + ["is-active", "--quiet", SERVICE_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    except Exception:
        return False


def start_suricata_ips() -> None:
    """Start the Suricata service via systemd."""

    try:
        subprocess.run(
            SYSTEMCTL + ["start", SERVICE_NAME],
            check=True,
        )
    except Exception:
        pass


def stop_suricata_ips() -> None:
    """Stop the Suricata service via systemd."""

    try:
        subprocess.run(
            SYSTEMCTL + ["stop", SERVICE_NAME],
            check=True,
        )

        checks = [
            ["sudo", "iptables", "-C", "INPUT", "-j", "NFQUEUE", "--queue-num", "0"],
            ["sudo", "iptables", "-C", "FORWARD", "-j", "NFQUEUE", "--queue-num", "0"],
            ["sudo", "iptables", "-C", "OUTPUT", "-j", "NFQUEUE", "--queue-num", "0"],
        ]

        for check in checks:
            if subprocess.run(check).returncode == 0:
                subprocess.run(["sudo", "iptables", "-D"] + check[3:])

    except Exception:
        pass


def reload_suricata_ips() -> None:
    """Reload the Suricata service configuration via systemd."""

    try:
        subprocess.run(
            SYSTEMCTL + ["reload", SERVICE_NAME],
            check=True,
        )
    except Exception:
        # Fallback to restart if reload fails
        try:
            subprocess.run(
                SYSTEMCTL + ["restart", SERVICE_NAME],
                check=True,
            )
        except Exception:
            pass


def is_systemd_available() -> bool:
    """Check if systemd is available on this system."""

    try:
        result = subprocess.run(
            ["pidof", "systemd"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_suricata_unit_exists() -> bool:
    """Return True if suricata.service exists on this system."""
    try:
        result = subprocess.run(
            ["systemctl", "list-unit-files", SERVICE_NAME + ".service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return SERVICE_NAME + ".service" in result.stdout
    except Exception:
        return False

