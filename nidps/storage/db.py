"""
db.py

Database layer for NIDPS.

Responsibilities:
- Host tracking
- Alert logging
- Blacklist / whitelist audit logs
- Event policy overrides
- Custom packet rules

Design:
- YAML holds defaults and tuning
- DB holds runtime memory, logs, user overrides, and custom rules
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional


# ===================== DATABASE FILE ===================== #

DB_FILE = "nidps.db"


# ===================== CONNECTION ===================== #

def get_conn() -> sqlite3.Connection:
    """
    Open a SQLite connection and enable dict-like row access.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def now_ts() -> str:
    """
    Current timestamp in ISO format.
    """
    return datetime.now().isoformat(timespec="seconds")


# ===================== INITIALIZATION ===================== #

def init_db() -> None:
    """
    Create all required tables if they do not exist.
    Safe to call on every startup.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS hosts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT UNIQUE NOT NULL,
        ip TEXT,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        is_whitelisted INTEGER DEFAULT 0,
        is_blacklisted INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        src_ip TEXT,
        src_mac TEXT,
        message TEXT NOT NULL,
        reason TEXT
    );

    CREATE TABLE IF NOT EXISTS blacklist_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT NOT NULL,
        reason TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS whitelist_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT NOT NULL,
        reason TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT UNIQUE NOT NULL,
        alert INTEGER NOT NULL,
        blacklist INTEGER NOT NULL,
        write_rule INTEGER NOT NULL,
        drop_flag INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS custom_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enabled INTEGER DEFAULT 1,

        name TEXT,
        src_ip TEXT,
        dst_ip TEXT,
        src_mac TEXT,
        dst_port INTEGER,
        protocol TEXT,

        action_alert INTEGER DEFAULT 0,
        action_block INTEGER DEFAULT 0,
        action_drop INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()


# ===================== HOST TRACKING ===================== #

def upsert_host(mac: str, ip: str) -> None:
    """
    Insert or update host information.
    """
    if not mac:
        return

    conn = get_conn()
    cur = conn.cursor()
    ts = now_ts()

    cur.execute("""
        INSERT INTO hosts (mac, ip, first_seen, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            ip = excluded.ip,
            last_seen = excluded.last_seen
    """, (mac.lower(), ip, ts, ts))

    conn.commit()
    conn.close()


def set_host_whitelisted(mac: str, value: bool) -> None:
    """
    Update host whitelist state.
    """
    conn = get_conn()
    cur = conn.cursor()
    ts = now_ts()

    cur.execute("""
        INSERT INTO hosts (mac, first_seen, last_seen, is_whitelisted)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            is_whitelisted = excluded.is_whitelisted,
            last_seen = excluded.last_seen
    """, (mac.lower(), ts, ts, int(value)))

    conn.commit()
    conn.close()


def set_host_blacklisted(mac: str, value: bool) -> None:
    """
    Update host blacklist state.
    """
    conn = get_conn()
    cur = conn.cursor()
    ts = now_ts()

    cur.execute("""
        INSERT INTO hosts (mac, first_seen, last_seen, is_blacklisted)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            is_blacklisted = excluded.is_blacklisted,
            last_seen = excluded.last_seen
    """, (mac.lower(), ts, ts, int(value)))

    conn.commit()
    conn.close()


# ===================== ALERT LOGGING ===================== #

def log_alert(event_type: str, ip: str, mac: str, message: str, reason: str = None) -> None:
    """
    Store alert in DB.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO alerts (timestamp, event_type, src_ip, src_mac, message, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        now_ts(),
        event_type,
        ip,
        mac.lower() if mac else mac,
        message,
        reason
    ))

    conn.commit()
    conn.close()


# ===================== BLACKLIST / WHITELIST LOGS ===================== #

def blacklist_mac(mac: str, reason: str) -> None:
    """
    Log blacklist action and mark host blacklisted.
    """
    conn = get_conn()
    cur = conn.cursor()
    ts = now_ts()

    cur.execute("""
        INSERT INTO blacklist_log (mac, reason, timestamp)
        VALUES (?, ?, ?)
    """, (mac.lower(), reason, ts))

    cur.execute("""
        INSERT INTO hosts (mac, first_seen, last_seen, is_blacklisted)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(mac) DO UPDATE SET
            is_blacklisted = 1,
            last_seen = excluded.last_seen
    """, (mac.lower(), ts, ts))

    conn.commit()
    conn.close()


def whitelist_mac(mac: str, reason: str) -> None:
    """
    Log whitelist action and mark host whitelisted.
    """
    conn = get_conn()
    cur = conn.cursor()
    ts = now_ts()

    cur.execute("""
        INSERT INTO whitelist_log (mac, reason, timestamp)
        VALUES (?, ?, ?)
    """, (mac.lower(), reason, ts))

    cur.execute("""
        INSERT INTO hosts (mac, first_seen, last_seen, is_whitelisted)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(mac) DO UPDATE SET
            is_whitelisted = 1,
            last_seen = excluded.last_seen
    """, (mac.lower(), ts, ts))

    conn.commit()
    conn.close()


# ===================== EVENT POLICY OVERRIDES ===================== #

def save_policy(event_type: str, policy) -> None:
    """
    Save an event policy override.
    This stores only the user's chosen final policy for that event type.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO rules (event_type, alert, blacklist, write_rule, drop_flag)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(event_type) DO UPDATE SET
            alert = excluded.alert,
            blacklist = excluded.blacklist,
            write_rule = excluded.write_rule,
            drop_flag = excluded.drop_flag
    """, (
        event_type,
        int(policy.alert),
        int(policy.blacklist),
        int(policy.write_rule),
        int(policy.drop)
    ))

    conn.commit()
    conn.close()


def load_policies():
    """
    Load all event policy overrides.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rules")
    rows = cur.fetchall()

    conn.close()
    return rows


def delete_policy(event_type: str) -> None:
    """
    Delete a policy override so config defaults take effect again.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM rules WHERE event_type = ?", (event_type,))

    conn.commit()
    conn.close()


# ===================== CUSTOM RULES ===================== #

def add_custom_rule(
    name: str,
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    src_mac: Optional[str] = None,
    dst_port: Optional[int] = None,
    protocol: Optional[str] = None,
    action_alert: bool = False,
    action_block: bool = False,
    action_drop: bool = False,
    enabled: bool = True,
) -> int:
    """
    Add a custom packet rule.

    Returns:
        New rule ID
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO custom_rules (
            enabled,
            name,
            src_ip,
            dst_ip,
            src_mac,
            dst_port,
            protocol,
            action_alert,
            action_block,
            action_drop
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(enabled),
        name,
        src_ip,
        dst_ip,
        src_mac.lower() if src_mac else None,
        dst_port,
        protocol.upper() if protocol else None,
        int(action_alert),
        int(action_block),
        int(action_drop),
    ))

    rule_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rule_id


def get_custom_rules(enabled_only: bool = True):
    """
    Load custom rules.
    """
    conn = get_conn()
    cur = conn.cursor()

    if enabled_only:
        cur.execute("SELECT * FROM custom_rules WHERE enabled = 1 ORDER BY id ASC")
    else:
        cur.execute("SELECT * FROM custom_rules ORDER BY id ASC")

    rows = cur.fetchall()
    conn.close()
    return rows


def update_custom_rule(
    rule_id: int,
    *,
    enabled: Optional[bool] = None,
    name: Optional[str] = None,
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    src_mac: Optional[str] = None,
    dst_port: Optional[int] = None,
    protocol: Optional[str] = None,
    action_alert: Optional[bool] = None,
    action_block: Optional[bool] = None,
    action_drop: Optional[bool] = None,
) -> None:
    """
    Update only the provided fields of a custom rule.
    """
    updates = []
    params = []

    def add(field, value):
        updates.append(f"{field} = ?")
        params.append(value)

    if enabled is not None:
        add("enabled", int(enabled))
    if name is not None:
        add("name", name)
    if src_ip is not None:
        add("src_ip", src_ip)
    if dst_ip is not None:
        add("dst_ip", dst_ip)
    if src_mac is not None:
        add("src_mac", src_mac.lower() if src_mac else None)
    if dst_port is not None:
        add("dst_port", dst_port)
    if protocol is not None:
        add("protocol", protocol.upper() if protocol else None)
    if action_alert is not None:
        add("action_alert", int(action_alert))
    if action_block is not None:
        add("action_block", int(action_block))
    if action_drop is not None:
        add("action_drop", int(action_drop))

    if not updates:
        return

    params.append(rule_id)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE custom_rules
        SET {", ".join(updates)}
        WHERE id = ?
    """, params)

    conn.commit()
    conn.close()


def delete_custom_rule(rule_id: int) -> None:
    """
    Delete a custom rule.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM custom_rules WHERE id = ?", (rule_id,))

    conn.commit()
    conn.close()

# ===================== HOST + ALERT LOOKUPS ===================== #

def get_all_hosts():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM hosts ORDER BY last_seen DESC")
    rows = cur.fetchall()

    conn.close()
    return rows


def get_alerts_for_mac(mac: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM alerts
        WHERE src_mac = ?
        ORDER BY timestamp DESC
    """, (mac.lower(),))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_blacklist_history(mac: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM blacklist_log
        WHERE mac = ?
        ORDER BY timestamp DESC
    """, (mac.lower(),))

    rows = cur.fetchall()
    conn.close()
    return rows


def remove_blacklist(mac: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE hosts
        SET is_blacklisted = 0
        WHERE mac = ?
    """, (mac.lower(),))

    conn.commit()
    conn.close()