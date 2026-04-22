"""
config.py

Unified configuration loader for NIDPS.

Responsibilities:
- Load safe default config from config_default.yaml
- Load user override config from config.yaml
- Merge both configs together
- Provide nested key lookup using dot notation
- Save user override config
- Reset user override config

Why this exists:
- config_default.yaml is the shipped safe baseline
- config.yaml is what the GUI / user edits
- deleting config.yaml acts as a full reset
"""

from __future__ import annotations

import copy
import os
from typing import Any

import yaml


# ===================== CONFIG PATHS ===================== #

DEFAULT_CONFIG_PATH = "config_default.yaml"
USER_CONFIG_PATH = "config.yaml"


# ===================== IN-MEMORY STATE ===================== #

CONFIG: dict[str, Any] = {}
DEFAULT_CONFIG: dict[str, Any] = {}
USER_CONFIG: dict[str, Any] = {}


# ===================== INTERNAL HELPERS ===================== #

def _load_yaml(path: str) -> dict[str, Any]:
    """
    Load a YAML file safely.
    Returns empty dict if file does not exist.
    """
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a top-level YAML object")

    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge override into base.
    Values in override always win.
    """
    merged = copy.deepcopy(base)

    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


# ===================== LOAD / RELOAD ===================== #

def load_config() -> None:
    """
    Load default config + user override config.
    Result goes into CONFIG.
    """
    global CONFIG
    global DEFAULT_CONFIG
    global USER_CONFIG

    DEFAULT_CONFIG = _load_yaml(DEFAULT_CONFIG_PATH)
    USER_CONFIG = _load_yaml(USER_CONFIG_PATH)

    CONFIG = _deep_merge(DEFAULT_CONFIG, USER_CONFIG)


def reload_config() -> None:
    """
    Reload config from disk.
    """
    load_config()


# ===================== READ API ===================== #

def get(key: str, default=None):
    """
    Nested config lookup using dot notation.

    Example:
        get("features.ssh", True)
        get("detection.portscan.threshold", 10)
    """
    parts = key.split(".")
    value = CONFIG

    for part in parts:
        if not isinstance(value, dict):
            return default
        value = value.get(part)

    return value if value is not None else default


def get_user_config() -> dict[str, Any]:
    """
    Return the raw user override config.
    Useful later for GUI editing.
    """
    return copy.deepcopy(USER_CONFIG)


def get_merged_config() -> dict[str, Any]:
    """
    Return the final merged config.
    Useful later for GUI display.
    """
    return copy.deepcopy(CONFIG)


# ===================== WRITE API ===================== #

def save_user_config(new_user_config: dict[str, Any]) -> None:
    """
    Save the user override config only.
    Does not touch config_default.yaml.
    """
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(new_user_config, f, sort_keys=False)

    reload_config()


def reset_user_config() -> None:
    """
    Reset config by deleting config.yaml.
    Safe defaults remain in config_default.yaml.
    """
    if os.path.exists(USER_CONFIG_PATH):
        os.remove(USER_CONFIG_PATH)

    reload_config()