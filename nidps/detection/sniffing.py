"""
sniffing.py

Packet capture and dispatch subsystem for the NIDPS.

Responsibilities:
- Capture packets using Scapy AsyncSniffer
- Deduplicate short-lived flows
- Feed packets into a thread pool for detection
- Optionally forward packets for PCAP batching
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from scapy.all import IP, Ether, TCP, UDP, AsyncSniffer

from nidps.config.config import get
from nidps.detection.detection import packet_handler


# ===================== WORKER POOL ===================== #

executor = None


# ===================== FLOW DEDUPLICATION ===================== #

_flow_tracker = {}


def _dedupe_window() -> float:
    """
    Read dedupe window from config.
    """
    return float(get("sniffer.dedupe_window", 0.5))


# ===================== SNIFFER HANDLE ===================== #

_sniffer: AsyncSniffer | None = None


# ===================== FLOW DEDUPE LOGIC ===================== #

def dupe_flow(src_ip: str, src_mac: str, dst_port: str) -> bool:
    """
    Basic short-window flow dedupe.
    Prevents flooding the detector with near-identical traffic.
    """
    now = time.time()
    key = f"{src_ip}-{src_mac}-{dst_port}"

    last = _flow_tracker.get(key)
    if last is not None and (now - last) < _dedupe_window():
        return False

    _flow_tracker[key] = now

    # Cleanup old entries to limit memory growth
    if len(_flow_tracker) > 10000:
        cutoff = now - 60
        for k, v in list(_flow_tracker.items()):
            if v < cutoff:
                _flow_tracker.pop(k, None)

    return True


# ===================== PACKET DISPATCH ===================== #

def thread_pool(packet, capture_cb=None) -> None:
    """
    - Forward packet to optional capture callback
    - Deduplicate flow
    - Submit packet to detection worker pool
    """
    if capture_cb is not None:
        try:
            capture_cb(packet)
        except Exception:
            pass

    if packet.haslayer(IP):
        src_ip = packet[IP].src
        if src_ip == "0.0.0.0":
            return
    else:
        src_ip = "Unknown"

    src_mac = packet[Ether].src if packet.haslayer(Ether) else "Unknown"

    if packet.haslayer(TCP):
        dst_port = str(packet[TCP].dport)
    elif packet.haslayer(UDP):
        dst_port = str(packet[UDP].dport)
    else:
        dst_port = "NA"

    if not dupe_flow(src_ip, src_mac, dst_port):
        return

    if executor is not None:
        executor.submit(packet_handler, packet)


# ===================== SNIFFER CONTROL ===================== #

def start_sniffer(interface: str, stop_event, capture_cb=None) -> None:
    """
    Start AsyncSniffer and block until stop_event is set.
    """
    global executor
    global _sniffer

    executor = ThreadPoolExecutor(
        max_workers=int(get("sniffer.threads", 4))
    )

    print(f"[NIDPS] Sniffing on {interface}")

    def _cb(pkt):
        thread_pool(pkt, capture_cb=capture_cb)

    _sniffer = AsyncSniffer(
        iface=interface,
        prn=_cb,
        store=False
    )

    _sniffer.start()

    while not stop_event.is_set():
        time.sleep(0.2)

    stop_sniffer()


def stop_sniffer() -> None:
    """
    Safely stop sniffer and worker pool.
    """
    global _sniffer

    try:
        if _sniffer is not None:
            try:
                _sniffer.stop()
            except Exception:
                pass
    finally:
        _sniffer = None

    try:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass