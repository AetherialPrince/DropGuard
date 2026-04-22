"""
Dependency Checker Module
=========================
Detects what dependencies are installed, missing, or need updating
"""

import subprocess
import sys
import importlib.util
from Installer.utils import log_info, log_warning, log_error, detect_os


class DependencyChecker:
    """
    Checks system for required dependencies
    """
    
    # Define all required dependencies
    PYTHON_PACKAGES = {
        'scapy': {
            'pip_name': 'scapy',
            'import_name': 'scapy',
            'description': 'Packet capture and manipulation library'
        },
        'psutil': {
            'pip_name': 'psutil',
            'import_name': 'psutil',
            'description': 'System and process utilities'
        }
    }
    
    SYSTEM_PACKAGES = {
        'suricata': {
            'debian': 'suricata',
            'redhat': 'suricata',
            'arch': 'suricata',
            'description': 'High-performance IDS/IPS engine'
        }
    }
    
    def __init__(self):
        self.os_type = detect_os()
        self.results = {
            'python_packages': {},
            'system_packages': {},
            'system_info': self._gather_system_info()
        }
    
    def _gather_system_info(self):
        """Gather system information"""
        return {
            'os': self.os_type,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_path': sys.executable,
        }
    
    def check_all(self):
        """
        Run all dependency checks
        Returns dict with results
        """
        log_info("Starting dependency check...")
        
        # Check Python packages
        for pkg_name, pkg_info in self.PYTHON_PACKAGES.items():
            status = self._check_python_package(
                pkg_info['import_name'],
                pkg_info['pip_name']
            )
            self.results['python_packages'][pkg_name] = {
                'status': status,
                'pip_name': pkg_info['pip_name'],
                'description': pkg_info['description']
            }
        
        # Check system packages
        for pkg_name, pkg_info in self.SYSTEM_PACKAGES.items():
            status = self._check_system_package(pkg_name, pkg_info)
            self.results['system_packages'][pkg_name] = {
                'status': status,
                'description': pkg_info['description']
            }
        
        # Summary
        self._log_summary()
        return self.results
    
    def _check_python_package(self, import_name, pip_name):
        """
        Check if a Python package is installed
        Returns: 'INSTALLED', 'MISSING', or 'ERROR'
        """
        try:
            # Try to import the module
            spec = importlib.util.find_spec(import_name)
            if spec is not None:
                log_info(f"[OK] Python package '{pip_name}' is installed")
                return 'INSTALLED'
            else:
                log_warning(f"[FAIL] Python package '{pip_name}' is missing")
                return 'MISSING'
        except Exception as e:
            log_error(f"Error checking '{pip_name}': {e}")
            return 'ERROR'
    
    def _check_system_package(self, pkg_name, pkg_info):
        """
        Check if a system package is installed
        Returns: 'INSTALLED', 'MISSING', or 'UNSUPPORTED_OS'
        """
        if self.os_type not in pkg_info:
            log_warning(f"System package '{pkg_name}' not supported on {self.os_type}")
            return 'UNSUPPORTED_OS'
        
        try:
            # Check if package command exists
            result = subprocess.run(
                ['which', pkg_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                log_info(f"[OK] System package '{pkg_name}' is installed")
                return 'INSTALLED'
            else:
                log_warning(f"[FAIL] System package '{pkg_name}' is missing")
                return 'MISSING'
                
        except subprocess.TimeoutExpired:
            log_error(f"Timeout checking '{pkg_name}'")
            return 'ERROR'
        except Exception as e:
            log_error(f"Error checking '{pkg_name}': {e}")
            return 'ERROR'
    
    def _log_summary(self):
        """Log summary of dependency check"""
        log_info("="*60)
        log_info("DEPENDENCY CHECK SUMMARY")
        log_info("="*60)
        
        # Python packages summary
        py_total = len(self.results['python_packages'])
        py_installed = sum(1 for p in self.results['python_packages'].values() 
                          if p['status'] == 'INSTALLED')
        log_info(f"Python Packages: {py_installed}/{py_total} installed")
        
        # System packages summary
        sys_total = len(self.results['system_packages'])
        sys_installed = sum(1 for p in self.results['system_packages'].values() 
                           if p['status'] == 'INSTALLED')
        log_info(f"System Packages: {sys_installed}/{sys_total} installed")
        
        log_info("="*60)
    
    def get_missing_packages(self):
        """
        Get lists of missing packages
        Returns dict with 'python' and 'system' lists
        """
        missing = {
            'python': [],
            'system': []
        }
        
        for pkg_name, pkg_data in self.results['python_packages'].items():
            if pkg_data['status'] == 'MISSING':
                missing['python'].append(pkg_name)
        
        for pkg_name, pkg_data in self.results['system_packages'].items():
            if pkg_data['status'] == 'MISSING':
                missing['system'].append(pkg_name)
        
        return missing
    
    def needs_installation(self):
        """
        Check if any installations are needed
        Returns True if installations needed
        """
        missing = self.get_missing_packages()
        return len(missing['python']) > 0 or len(missing['system']) > 0
    
    def get_installation_plan(self):
        """
        Generate an installation plan
        Returns list of steps to execute
        """
        plan = []
        missing = self.get_missing_packages()
        
        # Python packages first (easier to install)
        for pkg in missing['python']:
            pkg_data = self.results['python_packages'][pkg]
            plan.append({
                'type': 'python',
                'name': pkg,
                'pip_name': pkg_data['pip_name'],
                'description': pkg_data['description']
            })
        
        # System packages (need sudo)
        for pkg in missing['system']:
            pkg_data = self.results['system_packages'][pkg]
            plan.append({
                'type': 'system',
                'name': pkg,
                'description': pkg_data['description']
            })
        
        return plan