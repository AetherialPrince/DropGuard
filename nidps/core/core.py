"""
core.py

Core runtime controller for the Network Intrusion Detection and
Prevention System (NIDPS).

Responsibilities:
- Load configuration
- Initialize DB
- Start and stop worker threads
- Manage packet capture for PCAP generation
- Emit runtime status events
"""

from __future__ import annotations

import os
import signal
import threading
import time
from datetime import datetime

from scapy.all import wrpcap

from nidps.config.config import load_config, get
from nidps.detection.sniffing import start_sniffer, stop_sniffer
from nidps.storage.storage import ensure_files, emit_pcap
from nidps.core.events import emit
from nidps.storage.db import init_db
from nidps.utils.logger import log_info
from nidps.detection.threats import reload_rule_engine


# ===================== GLOBAL RUNTIME STATE ===================== #

_stop_event = threading.Event()
_threads: list[threading.Thread] = []
_captured_packets = []
_lock = threading.Lock()


# ===================== SIGNAL HANDLING ===================== #

def _safe_quit(signum=None, frame=None):
    stop_nidps()


def install_signal_handlers():
    signal.signal(signal.SIGINT, _safe_quit)

    if hasattr(signal, "SIGQUIT"):
        signal.signal(signal.SIGQUIT, _safe_quit)


# ===================== PCAP CAPTURE ===================== #

def capture_for_pcap(packet):
    """
    Add packet to capture batch if PCAP feature is enabled.
    """
    if not get("features.pcap", True):
        return

    with _lock:
        _captured_packets.append(packet)


def _pcap_saver_loop():
    """
    Periodically flush buffered packets to a PCAP file.
    """
    ensure_files()

    interval_seconds = int(get("pcap.interval", 30))

    while not _stop_event.is_set():
        time.sleep(interval_seconds)

        if _stop_event.is_set():
            break

        if not get("features.pcap", True):
            continue

        with _lock:
            if not _captured_packets:
                continue

            batch = list(_captured_packets)
            _captured_packets.clear()

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join("Captures", f"capture_{ts}.pcap")

        try:
            wrpcap(path, batch)
            emit_pcap(path)
        except Exception:
            pass


# ===================== START / STOP ===================== #

def start_nidps(interface: str):
    """
    Start the NIDPS runtime.
    """
    # 1. Load config first
    load_config()

    # 2. Initialize filesystem / DB
    ensure_files()
    init_db()

    # 3. Reload rule engine after config + DB are ready
    reload_rule_engine()

    log_info(f"Starting NIDPS on {interface}")

    install_signal_handlers()
    _stop_event.clear()

    emit("status", f"[NIDPS] Starting on {interface}")

    sniff_thread = threading.Thread(
        target=start_sniffer,
        args=(interface, _stop_event, capture_for_pcap),
        daemon=True
    )

    _threads.clear()
    _threads.append(sniff_thread)

    if get("features.pcap", True):
        saver_thread = threading.Thread(
            target=_pcap_saver_loop,
            daemon=True
        )
        _threads.append(saver_thread)

    for t in _threads:
        t.start()

    emit("status", "[NIDPS] Started")


def stop_nidps():
    """
    Stop the NIDPS runtime.
    """
    emit("status", "[NIDPS] Stopping...")
    log_info("Stopping NIDPS")

    _stop_event.set()

    try:
        stop_sniffer()
    except Exception:
        pass

    emit("status", "[NIDPS] Stopped")