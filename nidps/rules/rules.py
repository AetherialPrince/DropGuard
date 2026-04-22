"""
rules.py

Core event policy engine for NIDPS.

This file handles built-in event types such as:
- NEW_HOST
- PORT_SCAN
- SSH
- FTP
- ARP_SPOOF

Design:
- Safe default policies come from config
- User overrides come from DB
- DB overrides always win
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nidps.config.config import get
from nidps.storage.db import load_policies, save_policy, delete_policy


# ===================== EVENT TYPES ===================== #

EVENT_PORT_SCAN = "PORT_SCAN"
EVENT_SSH = "SSH"
EVENT_FTP = "FTP"
EVENT_NEW_HOST = "NEW_HOST"

#=======================#
# HARDCODED RULES AREA
# Add future built-in event types here.
#=======================#

EVENT_ARP_SPOOF = "ARP_SPOOF"


# ===================== EVENT MODEL ===================== #

@dataclass
class Event:
    etype: str
    src_ip: str
    src_mac: str
    meta: dict = field(default_factory=dict)


# ===================== POLICY MODEL ===================== #

@dataclass
class Policy:
    alert: bool = True
    blacklist: bool = False
    write_rule: bool = False
    drop: bool = False


# ===================== RULE ENGINE ===================== #

class RuleEngine:
    """
    Event policy engine.

    Load order:
    1. config defaults
    2. DB overrides
    """

    def __init__(self):
        self.policies: dict[str, Policy] = {}
        self.reload()

    def _load_default_policies_from_config(self) -> dict[str, Policy]:
        """
        Build default policies from config.
        Also provide fallback values if config is missing entries.
        """
        rules_cfg = get("rules", {}) or {}
        policies: dict[str, Policy] = {}

        for event_type, cfg in rules_cfg.items():
            if not isinstance(cfg, dict):
                continue

            policies[event_type] = Policy(
                alert=bool(cfg.get("alert", True)),
                blacklist=bool(cfg.get("blacklist", False)),
                write_rule=bool(cfg.get("write_rule", False)),
                drop=bool(cfg.get("drop", False)),
            )

        # Fallback defaults in case config is incomplete
        fallback_defaults = {
            EVENT_NEW_HOST: Policy(alert=True, blacklist=False, write_rule=False, drop=False),
            EVENT_PORT_SCAN: Policy(alert=True, blacklist=True, write_rule=True, drop=True),
            EVENT_SSH: Policy(alert=True, blacklist=True, write_rule=True, drop=True),
            EVENT_FTP: Policy(alert=True, blacklist=True, write_rule=True, drop=True),
            EVENT_ARP_SPOOF: Policy(alert=True, blacklist=True, write_rule=True, drop=True),

            #=======================#
            # HARDCODED RULES AREA
            # Add future built-in default policies here.
            #=======================#
        }

        for event_type, policy in fallback_defaults.items():
            policies.setdefault(event_type, policy)

        return policies

    def _apply_db_overrides(self) -> None:
        """
        Apply DB overrides on top of config defaults.
        """
        try:
            rows = load_policies()
            for r in rows:
                self.policies[r["event_type"]] = Policy(
                    alert=bool(r["alert"]),
                    blacklist=bool(r["blacklist"]),
                    write_rule=bool(r["write_rule"]),
                    drop=bool(r["drop_flag"]),
                )
        except Exception:
            pass

    def reload(self) -> None:
        """
        Reload policies from config + DB.
        """
        self.policies = self._load_default_policies_from_config()
        self._apply_db_overrides()

    def decide(self, event: Event) -> Policy:
        """
        Resolve the final policy for an event.
        Falls back to alert-only if unknown.
        """
        return self.policies.get(event.etype, Policy(alert=True))

    def get_policy(self, event_type: str) -> Policy:
        """
        Return current final policy for a given event type.
        """
        return self.policies.get(event_type, Policy(alert=True))

    def set_policy(self, event_type: str, policy: Policy) -> None:
        """
        Set a policy override and persist it to DB.
        """
        self.policies[event_type] = policy

        try:
            save_policy(event_type, policy)
        except Exception:
            pass

    def reset_policy(self, event_type: str) -> None:
        """
        Remove DB override and fall back to config defaults.
        """
        try:
            delete_policy(event_type)
        except Exception:
            pass

        self.reload()

    def disable_event(self, event_type: str) -> None:
        """
        Fully disable response actions for one event type.
        """
        disabled = Policy(
            alert=False,
            blacklist=False,
            write_rule=False,
            drop=False,
        )
        self.set_policy(event_type, disabled)


# ===================== EVENT FACTORY ===================== #

def make_event(etype: str, ip: str, mac: str, **meta) -> Event:
    return Event(
        etype=etype,
        src_ip=ip,
        src_mac=mac,
        meta=meta,
    )