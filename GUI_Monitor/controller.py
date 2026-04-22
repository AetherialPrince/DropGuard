"""
Application controller responsible for coordinating the GUI and backend engine.

UPGRADES:
- Auto-whitelist local host MAC on startup
- Auto-whitelist router MAC on startup
- Cleaner startup flow
"""

from nidps.core.core import start_nidps, stop_nidps
from nidps.core.events import subscribe
from nidps.suricata.suricata_config import configure_suricata
from nidps.suricata.suricata_runtime import (
    ensure_nfqueue_rules,
    start_suricata_ips,
    stop_suricata_ips,
    is_suricata_unit_exists,
)

from nidps.storage.storage import add_whitelist
from nidps.storage.db import whitelist_mac
from nidps.detectors.arp_spoof import seed_baseline

import ipaddress
import psutil
import socket

from scapy.all import ARP, Ether, srp, conf


def detect_router_mac(iface: str) -> tuple[str, str] | tuple[None, None]:
    """Returns (router_ip, router_mac) or (None, None) on failure."""
    import subprocess as _sp

    router_ip = None

    try:
        for route in conf.route.routes:
            if route[3] == iface and route[2] not in ("0.0.0.0", "0", None):
                router_ip = route[2]
                break
    except Exception:
        pass

    if router_ip is None:
        addrs = psutil.net_if_addrs().get(iface, [])
        for addr in addrs:
            if addr.family == socket.AF_INET:
                if addr.address and addr.netmask:
                    network = ipaddress.IPv4Network(
                        f"{addr.address}/{addr.netmask}",
                        strict=False
                    )
                    router_ip = str(network.network_address + 1)
                    break

    if router_ip is None:
        return None, None

    # ── Try OS ARP cache first (immune to active-probe poisoning) ──
    # If the attacker is already running arpspoof, an active ARP probe
    # would get a poisoned reply. The OS neighbour table was populated
    # before the attack and is a safer source of truth.
    try:
        result = _sp.run(
            ["ip", "neigh", "show", router_ip],
            capture_output=True, text=True, timeout=3,
        )
        for line in result.stdout.splitlines():
            if "lladdr" in line:
                parts = line.split()
                idx = parts.index("lladdr")
                mac = parts[idx + 1].lower()
                return router_ip, mac
    except Exception:
        pass

    # ── Fall back to active ARP probe ──
    try:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=router_ip)
        ans, _ = srp(pkt, iface=iface, timeout=2, verbose=0)
        if ans:
            return router_ip, ans[0][1].hwsrc.lower()
    except Exception:
        pass

    return None, None


def detect_local_mac(iface: str) -> str | None:
    """
    Detect the real hardware MAC address for the selected interface.
    Prevents IPv6 addresses from being mistaken as MAC addresses.
    """
    try:
        addrs = psutil.net_if_addrs().get(iface, [])

        for addr in addrs:
            value = str(addr.address).strip().lower()

            if not value:
                continue

            # valid colon MAC
            parts = value.split(":")
            if len(parts) == 6 and all(len(p) == 2 for p in parts):
                return value

            # valid dash MAC
            parts = value.split("-")
            if len(parts) == 6 and all(len(p) == 2 for p in parts):
                return value.replace("-", ":")

    except Exception:
        pass

    return None

class AppController:
    def __init__(self, app):
        self.app = app
        self.ids_running = False

    #=======================#
    # START / STOP ENGINE
    #=======================#

    def toggle_ids(self):
        if not self.ids_running:
            iface = self.app.iface_map[self.app.iface_var.get()]

            # -------- Auto whitelist local machine --------
            local_mac = detect_local_mac(iface)
            if local_mac:
                add_whitelist(local_mac)
                whitelist_mac(local_mac, "auto-local-host")
                print(f"[DropGuard] Local MAC {local_mac} added to whitelist")

            # -------- Auto whitelist router --------
            router_ip, router_mac = detect_router_mac(iface)
            if router_mac:
                add_whitelist(router_mac)
                whitelist_mac(router_mac, "auto-router")
                print(f"[DropGuard] Router MAC {router_mac} added to whitelist")

            # -------- Seed ARP spoof baseline --------
            # Give the detector the known gateway IP/MAC before sniffing starts
            # so it can't be tricked by an attacker whose packet arrives first.
            if router_ip and router_mac:
                seed_baseline(router_ip, router_mac)
                print(f"[DropGuard] ARP baseline seeded: {router_ip} -> {router_mac}")

            try:
                configure_suricata(iface)
            except Exception as e:
                print(f"[DropGuard] Suricata config failed: {e}")

            try:
                ensure_nfqueue_rules()
            except Exception as e:
                print(f"[DropGuard] NFQUEUE setup failed: {e}")

            if not is_suricata_unit_exists():
                print("[DropGuard] Suricata systemd unit not found.")
                return

            try:
                start_suricata_ips()
            except Exception as e:
                print(f"[DropGuard] Suricata start failed: {e}")

            start_nidps(iface)

            self.app.status_var.set("PROTECTED")
            self.app.set_status_indicator(True)
            self.app.start_button.config(text="Stop IDS")
            self.ids_running = True

        else:
            stop_nidps()

            try:
                stop_suricata_ips()
            except Exception as e:
                print(f"[DropGuard] Suricata stop failed: {e}")

            self.app.status_var.set("STOPPED")
            self.app.set_status_indicator(False)
            self.app.start_button.config(text="Start IDS")
            self.ids_running = False

    #=======================#
    # UI EVENT BRIDGE
    #=======================#

    def on_packet(self, row):
        self.app.pages["Live Traffic"].add_packet(row)
        self.app.pages["Dashboard"].refresh_stats()

    def on_alert(self, msg):
        self.app.pages["Alerts"].add_alert(msg)
        self.app.pages["Dashboard"].refresh_stats()
        self.app.pages["Dashboard"].add_alert_preview(msg)

    def on_blacklist(self, mac):
        self.app.pages["Blacklist"].add_mac(mac)
        self.app.pages["Dashboard"].refresh_stats()

    def on_whitelist(self, mac):
        self.app.pages["Whitelist"].add_mac(mac)
        self.app.pages["Dashboard"].refresh_stats()

    def on_rule(self, rule):
        self.app.pages["Suricata Rules"].append_rule(rule)
        self.app.pages["Dashboard"].refresh_stats()

    def wire_events(self):
        subscribe("packet", self.app.ui_safe(self.on_packet))
        subscribe("alert", self.app.ui_safe(self.on_alert))
        subscribe("blacklist", self.app.ui_safe(self.on_blacklist))
        subscribe("whitelist", self.app.ui_safe(self.on_whitelist))
        subscribe("rule", self.app.ui_safe(self.on_rule))
        subscribe("pcap", self.app.ui_safe(self.app.pages["PCAP Manager"].set_latest))
        subscribe("status", self.app.ui_safe(self.app.pages["Alerts"].add_alert))