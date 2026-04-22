# nidps/telemetry.py
# Central in-memory telemetry store for DropGuard IDS
# Holds host state, alert history, and global statistics

from __future__ import annotations
import time

#=========== STATE ===========#

_hosts = {}
_alerts = []

_stats = {
    "packets": 0,
    "alerts": 0,
    "hosts": 0,
}


#=========== HOST TRACKING ===========#

def record_packet(mac: str, ip: str):

    now = time.time()

    if mac not in _hosts:
        _hosts[mac] = {
            "ip": ip,
            "first_seen": now,
            "last_seen": now,
            "packet_count": 1,
            "alert_count": 0,
            "attacks": []
        }
        _stats["hosts"] += 1

    else:
        h = _hosts[mac]
        h["last_seen"] = now
        h["packet_count"] += 1
        h["ip"] = ip

    _stats["packets"] += 1


#=========== ALERT TRACKING ===========#

def record_alert(alert_type: str, mac: str, ip: str, message: str):

    now = time.strftime("%H:%M:%S")

    _alerts.append({
        "time": now,
        "type": alert_type,
        "mac": mac,
        "ip": ip,
        "message": message
    })

    if mac in _hosts:
        _hosts[mac]["alert_count"] += 1
        if alert_type not in _hosts[mac]["attacks"]:
            _hosts[mac]["attacks"].append(alert_type)

    _stats["alerts"] += 1


#=========== READ API ===========#

def get_hosts():
    return _hosts

def get_alerts():
    return _alerts

def get_stats():
    return _stats