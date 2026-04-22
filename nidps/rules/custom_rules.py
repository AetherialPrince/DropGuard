# nidps/custom_rules.py

from __future__ import annotations

import ipaddress

from scapy.all import IP, Ether, TCP, UDP
from scapy.layers.inet import ICMP

from nidps.config.config import get
from nidps.storage.db import (
    get_custom_rules,
    log_alert,
    blacklist_mac as db_blacklist_mac,
)
from nidps.core.events import emit
from nidps.utils.logger import log_info, log_warning
from nidps.storage.storage import alert_timestamp, add_blacklist
from nidps.suricata.suricata_writer import block_mac_ips


def _packet_protocol(packet):
    """
    Normalize protocol name for rule matching.
    """
    if packet.haslayer(TCP):
        return "TCP"
    if packet.haslayer(UDP):
        return "UDP"
    if packet.haslayer(ICMP):
        return "ICMP"
    if packet.haslayer(IP):
        return "IP"
    return "OTHER"


def _packet_src_ip(packet):
    return packet[IP].src if packet.haslayer(IP) else None


def _packet_dst_ip(packet):
    return packet[IP].dst if packet.haslayer(IP) else None


def _packet_src_mac(packet):
    return packet[Ether].src.lower() if packet.haslayer(Ether) else None


def _packet_dst_port(packet):
    if packet.haslayer(TCP):
        return packet[TCP].dport
    if packet.haslayer(UDP):
        return packet[UDP].dport
    return None


def _is_home_ip(ip: str | None) -> bool:
    """
    Treat RFC1918/private IPv4 or IPv6 as HOME.
    """
    if not ip:
        return False

    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _match_ip(rule_ip: str | None, packet_ip: str | None) -> bool:
    """
    Supports:
    - empty/None => wildcard
    - HOME => private/home address
    - exact IP
    - CIDR notation (example: 192.168.1.0/24)
    """
    if not rule_ip:
        return True

    if not packet_ip:
        return False

    rule_ip = rule_ip.strip()

    if not rule_ip:
        return True

    if rule_ip.upper() == "ANY":
        return True

    if rule_ip.upper() == "HOME":
        return _is_home_ip(packet_ip)

    try:
        if "/" in rule_ip:
            return ipaddress.ip_address(packet_ip) in ipaddress.ip_network(rule_ip, strict=False)
        return packet_ip == rule_ip
    except ValueError:
        return False


def _match_mac(rule_mac: str | None, packet_mac: str | None) -> bool:
    """
    MAC match with explicit failure if packet has no MAC.
    """
    if not rule_mac:
        return True

    if not packet_mac:
        return False

    return rule_mac.strip().lower() == packet_mac.strip().lower()


def _match_port(rule_port, packet_port) -> bool:
    """
    Port match with explicit handling for packets without TCP/UDP ports.
    """
    if rule_port is None:
        return True

    if packet_port is None:
        return False

    return int(rule_port) == int(packet_port)


def _match_protocol(rule_protocol: str | None, packet_protocol: str) -> bool:
    """
    Protocol match; empty means wildcard.
    """
    if not rule_protocol:
        return True

    return rule_protocol.strip().upper() == packet_protocol.upper()


def rule_matches_packet(packet, rule):
    """
    Decide whether one DB-backed custom rule matches the packet.
    """
    src_ip = _packet_src_ip(packet)
    dst_ip = _packet_dst_ip(packet)
    src_mac = _packet_src_mac(packet)
    dst_port = _packet_dst_port(packet)
    protocol = _packet_protocol(packet)

    if not _match_ip(rule["src_ip"], src_ip):
        return False

    if not _match_ip(rule["dst_ip"], dst_ip):
        return False

    if not _match_mac(rule["src_mac"], src_mac):
        return False

    if not _match_port(rule["dst_port"], dst_port):
        return False

    if not _match_protocol(rule["protocol"], protocol):
        return False

    return True


def apply_custom_rules(packet, src_ip, src_mac):
    """
    Evaluate enabled custom rules in DB order.

    Behavior:
    - A matching DROP rule immediately returns DROP
    - ALERT/BLOCK actions can still log/block even if later rules are checked
    - If at least one non-drop rule matched, returns ALERT
    - Otherwise returns None
    """
    if not get("features.custom_rules", True):
        return None

    rules = get_custom_rules(enabled_only=True)
    matched_non_drop = False

    for rule in rules:
        if not rule_matches_packet(packet, rule):
            continue

        rule_name = rule["name"] or f"rule_{rule['id']}"
        ts = alert_timestamp()
        msg = f"[{ts}] Custom rule matched: {rule_name}"

        # ===== ALERT =====
        if rule["action_alert"]:
            emit("alert", msg)

            log_alert(
                event_type="CUSTOM_RULE",
                ip=src_ip,
                mac=src_mac,
                message=msg,
                reason=rule_name,
            )

            log_info(msg)
            matched_non_drop = True

        # ===== BLACKLIST / BLOCK =====
        if rule["action_block"] and src_mac:
            add_blacklist(src_mac)
            db_blacklist_mac(src_mac, f"custom rule: {rule_name}")
            block_mac_ips(src_mac, f"custom rule: {rule_name}")

            log_warning(f"BLACKLISTED {src_mac} via rule {rule_name}")
            matched_non_drop = True

        # ===== DROP =====
        if rule["action_drop"]:
            return "DROP"

    if matched_non_drop:
        return "ALERT"

    return None