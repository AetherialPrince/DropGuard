"""
threats.py

Threat-specific response helper used during detection.

UPDATED:
- Time-based cooldown instead of one-shot suppression
- Supports repeated attacks after cooldown window
- Allows manual reset (for unblacklist)
"""

from __future__ import annotations

from scapy.all import IP, TCP
import time

from nidps.rules.rules import make_event, RuleEngine
from nidps.detection.responders import responder
from nidps.core import telemetry
from nidps.config.config import get


# ===================== RESPONSE TRACKING ===================== #

# (mac, event_type) -> last_trigger_timestamp
_responded_events: dict[tuple[str, str], float] = {}

# Lazy global rule engine instance
_rule_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    global _rule_engine

    if _rule_engine is None:
        _rule_engine = RuleEngine()

    return _rule_engine


def reload_rule_engine() -> None:
    global _rule_engine

    if _rule_engine is None:
        _rule_engine = RuleEngine()
    else:
        _rule_engine.reload()


# ===================== THREAT ENGINE ===================== #

class ThreatEngine:
    def __init__(self, packet):
        self.packet = packet

    # ---------------- INTERNAL GUARD ---------------- #

    def _in_cooldown(self, mac: str, event_type: str) -> bool:
        key = (mac, event_type)
        now = time.time()

        cooldown = get(f"detection.cooldown_seconds.{event_type}", 180)
        last_seen = _responded_events.get(key)

        if last_seen and (now - last_seen) < cooldown:
            return True

        # update timestamp BEFORE handling (prevents spam race)
        _responded_events[key] = now
        return False

    # ---------------- EVENT DISPATCH ---------------- #

    def _dispatch(self, etype: str, ip: str, mac: str, **meta):
        event = make_event(etype, ip, mac, **meta)
        policy = get_rule_engine().decide(event)
        responder.handle(event, policy)

    # ---------------- SSH ATTEMPT ---------------- #

    def ssh_attempt(self, ip: str, mac: str) -> None:
        if self._in_cooldown(mac, "SSH"):
            return

        dst_ip = self.packet[IP].dst if self.packet.haslayer(IP) else "?"
        dst_port = self.packet[TCP].dport if self.packet.haslayer(TCP) else "?"

        msg = f"SSH attempt from {mac} ({ip}) -> {dst_ip}:{dst_port}"
        telemetry.record_alert("SSH", mac, ip, msg)

        self._dispatch("SSH", ip, mac, dst=f"{dst_ip}:{dst_port}")

    # ---------------- FTP ATTEMPT ---------------- #

    def ftp_attempt(self, ip: str, mac: str) -> None:
        if self._in_cooldown(mac, "FTP"):
            return

        msg = f"FTP attempt from {mac} ({ip})"
        telemetry.record_alert("FTP", mac, ip, msg)

        self._dispatch("FTP", ip, mac)

    # ---------------- PORT SCAN ---------------- #

    def port_scan(self, ip: str, mac: str) -> None:
        if self._in_cooldown(mac, "PORT_SCAN"):
            return

        msg = f"Port scan detected from {mac} ({ip})"
        telemetry.record_alert("PORT_SCAN", mac, ip, msg)

        self._dispatch("PORT_SCAN", ip, mac)

    # ---------------- NEW HOST ---------------- #

    def new_host(self, ip: str, mac: str) -> None:
        msg = f"New Host Discovered: {mac} ({ip})"
        telemetry.record_alert("NEW_HOST", mac, ip, msg)

        self._dispatch("NEW_HOST", ip, mac)

    #----------------- ARP SPOOF ---------------- #
    def arp_spoof(
        self,
        ip: str,
        mac: str,
        *,
        previous_mac: str | None = None,
        gateway: bool = False,
    ) -> None:
        """
        Dispatch a hardcoded ARP spoof detection event.
        """
        if self._in_cooldown(mac, "ARP_SPOOF"):
            return

        if gateway:
            msg = (
                f"ARP spoof detected from {mac} ({ip}) - "
                f"gateway IP changed from {previous_mac or '?'} to {mac}"
            )
        else:
            msg = (
                f"ARP spoof detected from {mac} ({ip}) - "
                f"conflicts with previous MAC {previous_mac or '?'}"
            )

        telemetry.record_alert("ARP_SPOOF", mac, ip, msg)

        self._dispatch(
            "ARP_SPOOF",
            ip,
            mac,
            previous_mac=previous_mac,
            gateway=gateway,
        )

    #=======================#
    # HARDCODED RULES AREA
    # Add future hardcoded threat dispatch methods here.
    #=======================#


# ===================== RESET SUPPORT ===================== #

def reset_mac_cooldown(mac: str):
    """
    Clears cooldown entries for a MAC.
    Call this when user unblacklists a device.
    """
    global _responded_events

    _responded_events = {
        k: v for k, v in _responded_events.items() if k[0] != mac
    }