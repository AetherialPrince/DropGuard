"""
portscan.py

Port scan detector.

Purpose:
- Track destination port diversity per source IP
- Trigger when the count of unique destination ports
  within the configured time window reaches threshold
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from nidps.config.config import get


# ===================== IN-MEMORY STATE ===================== #

_port_activity = defaultdict(lambda: deque())


# ===================== DETECTOR ===================== #

def check(packet, src_ip, src_mac, threat):
    """
    Detect simple port scan behavior.
    """
    if not get("features.portscan", True):
        return None

    port = ""

    if packet.haslayer("TCP"):
        port = str(packet["TCP"].dport)
    elif packet.haslayer("UDP"):
        port = str(packet["UDP"].dport)

    now = time.time()

    ports = _port_activity[src_ip]
    ports.append((now, port))

    window = get("detection.portscan.window", 10)
    threshold = get("detection.portscan.threshold", 10)

    while ports and (now - ports[0][0]) > window:
        ports.popleft()

    unique_ports = {p for _, p in ports if p}

    if len(unique_ports) >= threshold:
        threat.port_scan(src_ip, src_mac)
        return "ALERT"

    return None