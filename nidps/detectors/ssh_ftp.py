"""
ssh_ftp.py

Simple service detector for SSH and FTP attempts.

Purpose:
- Detect outbound/inbound packet destination ports
- Respect feature toggles from config
"""

from __future__ import annotations

from nidps.config.config import get


# ===================== DETECTOR ===================== #

def check(packet, src_ip, src_mac, threat):
    """
    Detect SSH / FTP traffic by destination port.
    """
    if not packet.haslayer("TCP"):
        return None

    dport = packet["TCP"].dport

    # SSH
    if get("features.ssh", True) and dport == 22:
        threat.ssh_attempt(src_ip, src_mac)
        return "ALERT"

    # FTP
    if get("features.ftp", True) and dport == 21:
        threat.ftp_attempt(src_ip, src_mac)
        return "ALERT"

    return None