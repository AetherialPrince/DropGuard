"""
Verification Module
===================
Post-installation verification checks
"""

import subprocess
import importlib
import os
from pathlib import Path
from Installer.utils import log_info, log_error, log_success, log_warning


class VerificationManager:
    """
    Verifies installation success and system readiness
    """
    
    def __init__(self):
        self.verification_results = {}
    
    def verify_all(self):
        """
        Run all verification checks
        Returns: dict with verification results
        """
        log_info("="*60)
        log_info("STARTING POST-INSTALLATION VERIFICATION")
        log_info("="*60)
        
        self.verification_results = {
            'python_imports': self._verify_python_imports(),
            'system_packages': self._verify_system_packages(),
            'directories': self._verify_directories(),
            'permissions': self._verify_permissions(),
            'suricata_service': self._verify_suricata_service()
        }
        
        self._log_verification_summary()
        return self.verification_results
    
    def _verify_python_imports(self):
        """
        Verify Python packages can be imported
        """
        log_info("\nVerifying Python imports...")
        results = {}
        
        packages_to_test = {
            'scapy': 'scapy',
            'psutil': 'psutil',
            'tkinter': 'tkinter'
        }
        
        for name, import_name in packages_to_test.items():
            try:
                importlib.import_module(import_name)
                results[name] = {
                    'status': 'PASS',
                    'message': f'Successfully imported {name}'
                }
                log_success(f"[OK] Can import {name}")
            except ImportError as e:
                results[name] = {
                    'status': 'FAIL',
                    'message': f'Cannot import {name}: {str(e)}'
                }
                log_error(f"[FAIL] Cannot import {name}: {e}")
        
        return results
    
    def _verify_system_packages(self):
        """
        Verify system packages are accessible
        """
        log_info("\nVerifying system packages...")
        results = {}
        
        packages = ['suricata']
        
        for pkg in packages:
            try:
                result = subprocess.run(
                    ['which', pkg],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    path = result.stdout.strip()
                    results[pkg] = {
                        'status': 'PASS',
                        'message': f'Found at {path}'
                    }
                    log_success(f"[OK] {pkg} found at {path}")
                else:
                    results[pkg] = {
                        'status': 'FAIL',
                        'message': f'{pkg} not found in PATH'
                    }
                    log_error(f"[FAIL] {pkg} not found in PATH")
                    
            except Exception as e:
                results[pkg] = {
                    'status': 'FAIL',
                    'message': f'Error checking {pkg}: {str(e)}'
                }
                log_error(f"[FAIL] Error checking {pkg}: {e}")
        
        return results
    
    def _verify_directories(self):
        """
        Verify required directories exist
        """
        log_info("\nVerifying directory structure...")
        results = {}
        
        required_dirs = [
            './Captures',
            './installation_logs',
            './assets',
            './views'
        ]
        
        for directory in required_dirs:
            path = Path(directory)
            if path.exists() and path.is_dir():
                results[directory] = {
                    'status': 'PASS',
                    'message': 'Directory exists'
                }
                log_success(f"[OK] {directory} exists")
            else:
                results[directory] = {
                    'status': 'FAIL',
                    'message': 'Directory not found'
                }
                log_error(f"[FAIL] {directory} not found")
        
        return results
    
    def _verify_permissions(self):
        """
        Verify write permissions for critical paths
        """
        log_info("\nVerifying file permissions...")
        results = {}
        
        paths_to_check = {
            './Captures': 'Packet capture directory',
            './installation_logs': 'Installation logs directory',
            '/var/lib/suricata/rules/local.rules': 'Suricata local rules file'
        }
        
        for path, description in paths_to_check.items():
            if os.path.exists(path):
                if os.access(path, os.W_OK):
                    results[path] = {
                        'status': 'PASS',
                        'message': f'Writable: {description}'
                    }
                    log_success(f"[OK] {path} is writable")
                else:
                    results[path] = {
                        'status': 'FAIL',
                        'message': f'Not writable: {description}'
                    }
                    log_warning(f"[WARN] {path} is not writable")
            else:
                results[path] = {
                    'status': 'SKIP',
                    'message': f'Path does not exist: {description}'
                }
                log_warning(f"[WARN] {path} does not exist")
        
        return results
    
    def _verify_suricata_service(self):
        """
        Check if Suricata service is available
        """
        log_info("\nVerifying Suricata service...")
        results = {}
        
        try:
            # Check if systemctl is available
            result = subprocess.run(
                ['systemctl', 'is-active', 'suricata'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            status = result.stdout.strip()
            
            if status == 'active':
                results['service_status'] = {
                    'status': 'PASS',
                    'message': 'Suricata service is active'
                }
                log_success("[OK] Suricata service is active")
            else:
                results['service_status'] = {
                    'status': 'INFO',
                    'message': f'Suricata service is {status} (can be started later)'
                }
                log_info(f"[INFO] Suricata service is {status}")
                
        except FileNotFoundError:
            results['service_status'] = {
                'status': 'SKIP',
                'message': 'systemctl not available (non-systemd system)'
            }
            log_info("[INFO] systemctl not available")
        except Exception as e:
            results['service_status'] = {
                'status': 'FAIL',
                'message': f'Error checking service: {str(e)}'
            }
            log_error(f"[FAIL] Error checking Suricata service: {e}")
        
        return results
    
    def _log_verification_summary(self):
        """Log summary of all verification checks"""
        log_info("\n" + "="*60)
        log_info("VERIFICATION SUMMARY")
        log_info("="*60)
        
        total_checks = 0
        passed = 0
        failed = 0
        skipped = 0
        
        for category, checks in self.verification_results.items():
            for check_name, check_result in checks.items():
                total_checks += 1
                status = check_result['status']
                
                if status == 'PASS':
                    passed += 1
                elif status == 'FAIL':
                    failed += 1
                elif status in ['SKIP', 'INFO']:
                    skipped += 1
        
        log_info(f"Total Checks: {total_checks}")
        log_info(f"Passed: {passed}")
        log_info(f"Failed: {failed}")
        log_info(f"Skipped/Info: {skipped}")
        log_info("="*60)
    
    def all_critical_checks_passed(self):
        """
        Check if all critical verifications passed
        Returns True if system is ready to use
        """
        # Python imports are critical
        py_checks = self.verification_results.get('python_imports', {})
        for check in py_checks.values():
            if check['status'] == 'FAIL':
                return False
        
        # Suricata package is critical
        sys_checks = self.verification_results.get('system_packages', {})
        if 'suricata' in sys_checks:
            if sys_checks['suricata']['status'] == 'FAIL':
                return False
        
        # Directory structure is critical
        dir_checks = self.verification_results.get('directories', {})
        for check in dir_checks.values():
            if check['status'] == 'FAIL':
                return False
        
        return True
    
    def get_recommendations(self):
        """
        Get recommendations for failed checks
        Returns list of recommendation strings
        """
        recommendations = []
        
        # Check Python imports
        py_checks = self.verification_results.get('python_imports', {})
        for pkg_name, check in py_checks.items():
            if check['status'] == 'FAIL':
                recommendations.append(
                    f"* Install {pkg_name}: pip install {pkg_name}"
                )
        
        # Check system packages
        sys_checks = self.verification_results.get('system_packages', {})
        if 'suricata' in sys_checks and sys_checks['suricata']['status'] == 'FAIL':
            recommendations.append(
                "* Install Suricata using your package manager (e.g., sudo apt install suricata)"
            )
        
        # Check permissions
        perm_checks = self.verification_results.get('permissions', {})
        for path, check in perm_checks.items():
            if check['status'] == 'FAIL':
                recommendations.append(
                    f"* Fix permissions for {path}: sudo chmod +w {path}"
                )
        
        # Suricata service
        service_check = self.verification_results.get('suricata_service', {}).get('service_status', {})
        if service_check.get('status') == 'INFO':
            recommendations.append(
                "* Start Suricata service: sudo systemctl start suricata"
            )
        
        return recommendations