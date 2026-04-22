"""
responders.py

Policy execution layer for the NIDPS.

Receives validated detection events along with their resolved
policy decisions and performs enforcement actions such as:
- Logging alerts
- Blacklisting MAC addresses
- Generating Suricata-compatible drop rules
"""

from __future__ import annotations

from nidps.storage.storage import (
    add_blacklist,
    alert_timestamp,
    log_alert,
    is_mac_safe,
)

from nidps.storage.db import log_alert as db_log_alert, blacklist_mac as db_blacklist_mac
from nidps.utils.logger import log_info, log_warning

from nidps.rules.rules import Event, Policy
from nidps.suricata.suricata_writer import block_mac_ips


#=========== RESPONSE ENGINE ===========#
# Applies enforcement actions based on policy decisions
# produced by the rule engine.

class Responder:

    def handle(self, event: Event, policy: Policy):

        ts = alert_timestamp()

        # -------- Alert Handling -------- #
        if policy.alert:
            self._alert(ts, event)

        # -------- Blacklist Handling -------- #
        if policy.blacklist:
            if is_mac_safe(event.src_mac):
                # Never blacklist a whitelisted MAC (e.g. false positive on gateway)
                log_warning(f"Skipping blacklist for whitelisted MAC {event.src_mac}")
            else:
                add_blacklist(event.src_mac)
                db_blacklist_mac(event.src_mac, event.etype)
                log_warning(f"Blacklisted {event.src_mac}")

        if policy.write_rule:
            block_mac_ips(event.src_mac, event.etype.lower())

    def _alert(self, ts, event):

        if event.etype == "NEW_HOST":
            msg = f"[{ts}] New Host Discovered: {event.src_mac} ({event.src_ip})"

        elif event.etype == "PORT_SCAN":
            msg = f"[{ts}] Port scan detected from {event.src_mac} ({event.src_ip})"

        elif event.etype == "SSH":
            dst = event.meta.get("dst", "?")
            msg = f"[{ts}] SSH attempt from {event.src_mac} ({event.src_ip}) -> {dst}"

        elif event.etype == "FTP":
            msg = f"[{ts}] FTP attempt from {event.src_mac} ({event.src_ip})"

        #=======================#
        # HARDCODED RULES AREA
        # Add future built-in alert message formats here.
        #=======================#

        elif event.etype == "ARP_SPOOF":
            previous_mac = event.meta.get("previous_mac", "?")
            gateway = bool(event.meta.get("gateway", False))

            if gateway:
                msg = (
                    f"[{ts}] ARP spoof detected from {event.src_mac} ({event.src_ip}) "
                    f"- gateway ownership changed from {previous_mac} to {event.src_mac}"
                )
            else:
                msg = (
                    f"[{ts}] ARP spoof detected from {event.src_mac} ({event.src_ip}) "
                    f"- conflicting ARP ownership with previous MAC {previous_mac}"
                )

        else:
            msg = f"[{ts}] Event {event.etype} from {event.src_mac} ({event.src_ip})"

        log_alert(msg)
        db_log_alert(event.etype, event.src_ip, event.src_mac, msg)
        log_info(msg)


responder = Responder()