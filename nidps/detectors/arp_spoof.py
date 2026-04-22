"""
arp_spoof.py

Hardcoded ARP spoofing detector.

Purpose:
- Detect repeated conflicting ARP claims for the same IP
- Optionally protect a known or learned gateway IP
- Provide a clear place for future hardcoded detector growth
"""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict, deque

from scapy.all import ARP

from nidps.config.config import get


# ===================== IN-MEMORY STATE ===================== #

# Current observed owner for each IP address.
_ip_to_mac: dict[str, str] = {}

# Conflict history:
# key = (claimed_ip, new_mac) -> timestamps of conflicting claims
_conflict_tracker: dict[tuple[str, str], deque[float]] = defaultdict(deque)

# Optional learned gateway identity.
_gateway_ip: str | None = None
_gateway_mac: str | None = None


#=======================#
# HARDCODED RULES AREA
# Add future hardcoded detector state and helper logic here.
#=======================#


# ===================== CONFIG HELPERS ===================== #

def _feature_enabled() -> bool:
    """
    Feature toggle for ARP spoof detection.
    """
    return bool(get("features.arp_spoof", True))


def _window_seconds() -> float:
    """
    Time window used for repeated conflicting ARP claims.
    """
    return float(get("detection.arp_spoof.window", 15))


def _conflict_threshold() -> int:
    """
    Number of repeated conflicting claims required before alerting.
    """
    return int(get("detection.arp_spoof.threshold", 3))


def _protect_gateway() -> bool:
    """
    Whether to immediately alert when the gateway IP changes MAC.
    """
    return bool(get("detection.arp_spoof.protect_gateway", True))


def _configured_gateway_ip() -> str | None:
    """
    Optional explicit gateway IP from config.
    """
    value = get("network.gateway_ip", None)
    if not value:
        return None

    value = str(value).strip()
    return value or None


# ===================== INTERNAL HELPERS ===================== #

def _is_private_ipv4(ip: str) -> bool:
    """
    True only for private IPv4 addresses.
    """
    try:
        addr = ipaddress.ip_address(ip)
        return addr.version == 4 and addr.is_private
    except ValueError:
        return False


def _looks_like_gateway_candidate(ip: str) -> bool:
    """
    Heuristic fallback:
    If no gateway is configured, treat x.x.x.1 private addresses as likely gateways.
    """
    return _is_private_ipv4(ip) and ip.endswith(".1")


def _trim_window(events: deque[float], now: float) -> None:
    """
    Keep only timestamps inside the configured detection window.
    """
    window = _window_seconds()

    while events and (now - events[0]) > window:
        events.popleft()


def _is_gratuitous_arp(arp_layer) -> bool:
    """
    Gratuitous ARP commonly announces:
    sender IP == target IP.
    """
    return bool(arp_layer.psrc and arp_layer.pdst and arp_layer.psrc == arp_layer.pdst)


def _should_inspect_claim(arp_layer) -> bool:
    """
    Only inspect ARP replies and gratuitous ARPs.
    This reduces noise from ordinary ARP requests.
    """
    if arp_layer.op == 2:  # is-at / reply
        return True

    if arp_layer.op == 1 and _is_gratuitous_arp(arp_layer):
        return True

    return False


def _learn_gateway_if_needed(claimed_ip: str, claimed_mac: str) -> None:
    """
    Learn or pin the gateway IP/MAC if configured or if a strong heuristic applies.
    """
    global _gateway_ip
    global _gateway_mac

    configured_ip = _configured_gateway_ip()

    if configured_ip:
        if _gateway_ip is None:
            _gateway_ip = configured_ip

        if claimed_ip == _gateway_ip and _gateway_mac is None:
            _gateway_mac = claimed_mac
        return

    if _gateway_ip is None and _looks_like_gateway_candidate(claimed_ip):
        _gateway_ip = claimed_ip

    if claimed_ip == _gateway_ip and _gateway_mac is None:
        _gateway_mac = claimed_mac


# ===================== SEED ===================== #

def seed_baseline(ip: str, mac: str) -> None:
    """
    Pre-load a known IP -> MAC mapping before sniffing starts.
    Called by controller.py with the detected gateway IP and MAC so the
    detector has ground truth from the first packet, rather than
    learning it from live traffic (which the attacker may reach first).

    Always pins the provided IP as the protected gateway, regardless of
    whether it looks like a .1 address, so multi-adapter VirtualBox setups
    (where the monitored gateway may not end in .1) are handled correctly.
    """
    global _gateway_ip, _gateway_mac

    ip  = ip.strip()
    mac = mac.strip().lower()

    if not ip or not mac:
        return

    _ip_to_mac[ip] = mac

    # Always treat the seeded IP as the protected gateway — the controller
    # explicitly resolved it as the real gateway for this interface.
    if _gateway_ip is None:
        _gateway_ip  = ip
        _gateway_mac = mac


# ===================== DETECTOR ===================== #

def check(packet, src_ip, src_mac, threat):
    """
    Detect ARP spoofing by watching conflicting IP -> MAC claims.

    Logic:
    - Ignore non-ARP packets
    - Focus on ARP replies and gratuitous ARPs
    - Learn the first observed owner for an IP
    - If a different MAC later claims the same IP repeatedly inside a time window,
      raise ARP_SPOOF
    - If a gateway IP changes MAC, alert immediately when gateway protection is enabled
    """
    global _gateway_mac

    if not _feature_enabled():
        return None

    if not packet.haslayer(ARP):
        return None

    arp_layer = packet[ARP]

    if not _should_inspect_claim(arp_layer):
        return None

    claimed_ip = (arp_layer.psrc or "").strip()
    claimed_mac = (arp_layer.hwsrc or "").strip().lower()

    if not claimed_ip or not claimed_mac:
        return None

    # Ignore empty / probe style addresses for spoof detection decisions.
    if claimed_ip == "0.0.0.0":
        return None

    _learn_gateway_if_needed(claimed_ip, claimed_mac)

    previous_mac = _ip_to_mac.get(claimed_ip)

    # First time we see the IP: learn and continue.
    if previous_mac is None:
        _ip_to_mac[claimed_ip] = claimed_mac

        if claimed_ip == _gateway_ip and _gateway_mac is None:
            _gateway_mac = claimed_mac

        return None

    # Same owner again: refresh baseline quietly.
    if previous_mac == claimed_mac:
        _ip_to_mac[claimed_ip] = claimed_mac

        if claimed_ip == _gateway_ip and _gateway_mac is None:
            _gateway_mac = claimed_mac

        return None

    # Gateway IP changed MAC: treat as high-confidence and alert immediately.
    if _protect_gateway() and claimed_ip == _gateway_ip:
        threat.arp_spoof(claimed_ip, claimed_mac, previous_mac=previous_mac, gateway=True)
        # Do NOT update _ip_to_mac or _gateway_mac — keep the known-good
        # baseline so every subsequent spoofed ARP keeps triggering detection.
        return "ALERT"

    # Generic conflicting claim: require repeated observations within a window.
    now = time.time()
    key = (claimed_ip, claimed_mac)
    history = _conflict_tracker[key]
    history.append(now)
    _trim_window(history, now)

    if len(history) >= _conflict_threshold():
        threat.arp_spoof(claimed_ip, claimed_mac, previous_mac=previous_mac, gateway=False)
        # Never overwrite the baseline for the gateway IP — even if the gateway
        # protection path didn't fire (e.g. _gateway_ip mismatch due to multiple
        # adapters), we must not let repeated attacker ARPs poison the known-good MAC.
        if claimed_ip != _gateway_ip:
            _ip_to_mac[claimed_ip] = claimed_mac
        return "ALERT"

    return None