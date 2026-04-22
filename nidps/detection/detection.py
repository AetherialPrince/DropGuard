"""
detection.py

Primary packet inspection pipeline for the NIDPS.

Responsibilities:
- Normalize packet context
- Track hosts
- Enforce whitelist / blacklist state
- Apply custom rules first
- Run built-in detectors second
- Emit packet rows for the GUI

Design order:
1. Ignore invalid packets
2. Host tracking
3. Whitelist / blacklist enforcement
4. Custom packet rules
5. Built-in detectors
6. GUI packet emission
"""

from __future__ import annotations

import time
from scapy.all import ARP, IP, Ether

from nidps.core import telemetry
from nidps.detection.threats import ThreatEngine
from nidps.storage.storage import (
    write_to_table,
    is_mac_safe,
    is_mac_blocked,
    alert_timestamp,
)
from nidps.core.events import emit
from nidps.suricata.suricata_writer import block_mac_ips
from nidps.rules.custom_rules import apply_custom_rules

from nidps.storage.db import upsert_host
from nidps.utils.logger import log_warning

# Use explicit detector imports here so adding new hardcoded detectors
# does not depend on a package __init__.py update.
from nidps.detectors.discovery import check as discovery_check
from nidps.detectors.portscan import check as portscan_check
from nidps.detectors.ssh_ftp import check as sshftp_check
from nidps.detectors.arp_spoof import check as arp_spoof_check


#=======================#
# HARDCODED RULES AREA
# Add future hardcoded detector imports and detector calls here.
#=======================#


def _packet_identity(packet) -> tuple[str | None, str]:
    """
    Extract the best available source identity from the packet.

    For IP traffic:
    - source IP comes from the IP layer

    For ARP traffic:
    - source IP comes from ARP.psrc

    MAC comes from Ether when present.
    """
    src_mac = packet[Ether].src if packet.haslayer(Ether) else "Unknown"

    if packet.haslayer(IP):
        return packet[IP].src, src_mac

    if packet.haslayer(ARP):
        return packet[ARP].psrc, src_mac

    return None, src_mac


def packet_handler(packet):
    """
    Main packet inspection entry point.
    """
    threat = ThreatEngine(packet)
    action = "PASS"

    src_ip, src_mac = _packet_identity(packet)

    # ---------------- PACKET FILTER ---------------- #
    if src_ip is None:
        return
    
    if packet.haslayer(IP) and src_ip == "0.0.0.0":
        return

    # ---------------- HOST TRACKING (FIXED POSITION) ---------------- #
    # ALWAYS track host, even if whitelisted.
    if src_mac != "Unknown":
        upsert_host(src_mac, src_ip)

    # ---------------- ARP SPOOF (pre-whitelist) ---------------- #
    # Must run before the whitelist return so the detector can observe
    # legitimate gateway ARP replies to build its MAC baseline.
    # Without this, whitelisted gateway packets never reach the detector
    # and the attacker's first spoofed ARP gets silently learned as truth.
    if packet.haslayer(ARP):
        arp_pre_result = arp_spoof_check(packet, src_ip, src_mac, threat)
    else:
        arp_pre_result = None

    # ---------------- WHITELIST ---------------- #
    if is_mac_safe(src_mac):
        emit("packet", (
            alert_timestamp(),
            src_ip,
            src_mac,
            _packet_protocol(packet),
            _packet_port(packet),
            "WHITELISTED"
        ))
        return

    # ---------------- TELEMETRY ---------------- #
    telemetry.record_packet(src_mac, src_ip)
    write_to_table(src_ip, src_mac)

    # ---------------- BLACKLIST ---------------- #
    if is_mac_blocked(src_mac):
        block_mac_ips(src_mac, "blacklisted host")
        action = "DROP"
        log_warning(f"Blocked {src_mac}")

    # ---------------- CUSTOM RULES ---------------- #
    custom_result = apply_custom_rules(packet, src_ip, src_mac)
    if custom_result:
        action = custom_result

        if action == "DROP":
            _emit_packet_row(packet, src_ip, src_mac, action)
            return

    # ---------------- BUILT-IN DETECTORS ---------------- #
    discovery_result = discovery_check(src_ip, src_mac, threat)
    if discovery_result:
        action = discovery_result

    #=======================#
    # HARDCODED RULES AREA
    # Add future hardcoded detector calls in this section.
    #=======================#

    if arp_pre_result:
        action = arp_pre_result

    # These detectors are IP/TCP/UDP oriented and already self-filter safely.
    portscan_result = portscan_check(packet, src_ip, src_mac, threat)
    if portscan_result:
        action = portscan_result

    svc_result = sshftp_check(packet, src_ip, src_mac, threat)
    if svc_result:
        action = svc_result

    # ---------------- FINAL CHECK ---------------- #
    if is_mac_blocked(src_mac):
        action = "DROP"

    _emit_packet_row(packet, src_ip, src_mac, action)


def _packet_protocol(packet) -> str:
    """
    Build a readable protocol label for the GUI row.
    """
    if packet.haslayer(ARP):
        return "ARP"
    if packet.haslayer("TCP"):
        return "TCP"
    if packet.haslayer("UDP"):
        return "UDP"
    if packet.haslayer(IP):
        return "IP"
    return "OTHER"


def _packet_port(packet) -> str:
    """
    Return destination port when applicable.
    """
    if packet.haslayer("TCP"):
        return str(packet["TCP"].dport)
    if packet.haslayer("UDP"):
        return str(packet["UDP"].dport)
    return ""


def _emit_packet_row(packet, src_ip: str, src_mac: str, action: str) -> None:
    """
    Build and emit the live packet row for the GUI.
    """
    row = (
        time.strftime("%H:%M:%S"),
        src_ip,
        src_mac,
        _packet_protocol(packet),
        _packet_port(packet),
        action
    )

    emit("packet", row)