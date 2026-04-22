"""
events.py

Lightweight thread-safe publish/subscribe event system used
for communication between backend NIDPS components and the GUI.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Any
import threading


# ===================== EVENT BUS STATE ===================== #

# Synchronizes access to subscriber registry
_lock = threading.Lock()

# Maps event type -> list of callbacks
_subscribers = {
    "alert": [],
    "packet": [],
    "blacklist": [],
    "whitelist": [],  
    "rule": [],
    "pcap": [],
    "status": [],
}


# ===================== SUBSCRIPTION API ===================== #

def subscribe(event_type: str, callback: Callable[[Any], None]) -> None:
    """
    Registers a callback function for the specified event type.

    :param event_type: Name of event channel
    :param callback: Function invoked when event is emitted
    """
    with _lock:
        _subscribers.setdefault(event_type, []).append(callback)


# ===================== EMISSION API ===================== #

def emit(event_type: str, data: Any) -> None:
    """
    Emits an event to all registered subscribers.

    :param event_type: Name of event channel
    :param data: Payload associated with event
    """

    with _lock:
        callbacks = list(_subscribers.get(event_type, []))

    for cb in callbacks:
        try:
            cb(data)
        except Exception:
            # Never let UI callbacks kill the IDS threads
            pass