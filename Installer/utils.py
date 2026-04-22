"""
Utility functions for the installer
Handles logging, OS detection, and helper functions
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path


# ========== LOGGING SETUP ========== #

_logger = None
_log_file = None


def setup_logging():
    """
    Setup logging system with timestamped log file
    Returns the log file path
    """
    global _logger, _log_file
    
    # Create logs directory
    log_dir = Path('./installation_logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _log_file = log_dir / f"install_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(_log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    _logger = logging.getLogger('DropGuardInstaller')
    _logger.info("="*60)
    _logger.info("DropGuard Installer Log Started")
    _logger.info(f"Python version: {sys.version}")
    _logger.info(f"OS: {detect_os()}")
    _logger.info("="*60)
    
    return str(_log_file)


def get_logger():
    """Get the installer logger instance"""
    global _logger
    if _logger is None:
        setup_logging()
    return _logger


def log_info(message):
    """Log info message"""
    get_logger().info(message)


def log_warning(message):
    """Log warning message"""
    get_logger().warning(message)


def log_error(message):
    """Log error message"""
    get_logger().error(message)


def log_success(message):
    """Log success message"""
    get_logger().info(f"[OK] {message}")


# ========== OS DETECTION ========== #

def detect_os():
    """
    Detect the operating system type
    Returns: 'debian', 'redhat', 'arch', 'windows', 'macos', 'unknown'
    """
    if sys.platform == 'win32':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif sys.platform.startswith('linux'):
        # Check /etc/os-release for Linux distro
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content:
                    return 'debian'
                elif 'fedora' in content or 'rhel' in content or 'centos' in content:
                    return 'redhat'
                elif 'arch' in content or 'manjaro' in content:
                    return 'arch'
        return 'linux'
    return 'unknown'


def get_package_manager():
    """
    Get the system package manager command
    Returns: ('apt', 'apt-get') or ('dnf',) or ('pacman', '-S') etc.
    """
    os_type = detect_os()
    
    if os_type == 'debian':
        return ('apt-get', 'install', '-y')
    elif os_type == 'redhat':
        return ('dnf', 'install', '-y')
    elif os_type == 'arch':
        return ('pacman', '-S', '--noconfirm')
    else:
        return None


# ========== FILE AND DIRECTORY HELPERS ========== #

def ensure_directory(path):
    """
    Ensure a directory exists, create if it doesn't
    Returns True if successful
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        log_info(f"Directory verified/created: {path}")
        return True
    except Exception as e:
        log_error(f"Failed to create directory {path}: {e}")
        return False


def check_write_permission(path):
    """
    Check if we have write permission to a path
    """
    try:
        if os.path.exists(path):
            return os.access(path, os.W_OK)
        else:
            # Check parent directory
            parent = os.path.dirname(path)
            return os.access(parent, os.W_OK) if os.path.exists(parent) else False
    except:
        return False


# ========== SYSTEM CHECKS ========== #

def is_root():
    """Check if running with root/sudo privileges"""
    return os.geteuid() == 0


def check_internet_connection():
    """
    Check if internet connection is available
    """
    import socket
    try:
        # Try to connect to Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


# ========== LOG MANAGEMENT ========== #

def cleanup_old_logs(keep=10):
    """
    Keep only the most recent N log files
    """
    try:
        log_dir = Path('./installation_logs')
        if not log_dir.exists():
            return
        
        log_files = sorted(log_dir.glob('install_*.log'), 
                          key=lambda x: x.stat().st_mtime,
                          reverse=True)
        
        # Remove old logs
        for old_log in log_files[keep:]:
            old_log.unlink()
            log_info(f"Removed old log: {old_log.name}")
    except Exception as e:
        log_warning(f"Could not cleanup old logs: {e}")


# ========== FORMATTING HELPERS ========== #

def format_size(bytes):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


def format_duration(seconds):
    """Format seconds to human readable duration"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"