"""
Installation Operations Module
===============================
Handles actual installation of packages
"""

import subprocess
import sys
import time
import os

from Installer.utils import (
    log_info, log_error, log_success, log_warning,
    detect_os, get_package_manager, is_root
)


class InstallationManager:
    """
    Manages installation of dependencies
    """

    def __init__(self, progress_callback=None):
        """
        Args:
            progress_callback: Function to call with progress updates
                              (step_name, status, message)
        """
        self.progress_callback = progress_callback
        self.os_type = detect_os()
        self.installed_packages = []
        self.failed_packages = []

    def _update_progress(self, step_name, status, message):
        """Update progress via callback"""
        if self.progress_callback:
            self.progress_callback(step_name, status, message)

        log_info(f"[{status}] {step_name}: {message}")

    # ==========================================================
    # PYTHON PACKAGE INSTALL
    # ==========================================================

    def install_python_package(self, pip_name, description):

        package_id = f"python:{pip_name}"
        self._update_progress(pip_name, 'INSTALLING', f'Installing {description}...')

        try:

            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                pip_name
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:

                self._update_progress(pip_name, 'SUCCESS', f'Successfully installed {pip_name}')
                self.installed_packages.append(package_id)
                log_success(f"Installed {pip_name}")
                return True

            else:

                error_msg = result.stderr if result.stderr else result.stdout
                self._update_progress(pip_name, 'FAILED', error_msg[:120])
                self.failed_packages.append(package_id)
                log_error(f"Failed to install {pip_name}: {error_msg}")
                return False

        except Exception as e:

            self._update_progress(pip_name, 'FAILED', str(e))
            self.failed_packages.append(package_id)
            log_error(f"Error installing {pip_name}: {e}")
            return False

    # ==========================================================
    # SYSTEM PACKAGE INSTALL
    # ==========================================================

    def install_system_package(self, pkg_name, description):

        package_id = f"system:{pkg_name}"
        self._update_progress(pkg_name, 'INSTALLING', f'Installing {description}...')

        if not is_root():
            msg = "Root privileges required for system packages"
            self._update_progress(pkg_name, 'FAILED', msg)
            log_error(f"Cannot install {pkg_name}: {msg}")
            self.failed_packages.append(package_id)
            return False

        pkg_mgr = get_package_manager()

        if pkg_mgr is None:
            msg = f"Unsupported OS: {self.os_type}"
            self._update_progress(pkg_name, 'FAILED', msg)
            log_error(f"Cannot install {pkg_name}: {msg}")
            self.failed_packages.append(package_id)
            return False

        try:

            if self.os_type == "debian":
                subprocess.run(["apt-get", "update"], capture_output=True)

            cmd = list(pkg_mgr) + [pkg_name]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:

                self._update_progress(pkg_name, 'SUCCESS', f'Successfully installed {pkg_name}')
                self.installed_packages.append(package_id)
                log_success(f"Installed {pkg_name}")
                return True

            else:

                error_msg = result.stderr if result.stderr else result.stdout
                self._update_progress(pkg_name, 'FAILED', error_msg[:120])
                self.failed_packages.append(package_id)
                log_error(f"Failed to install {pkg_name}: {error_msg}")
                return False

        except Exception as e:

            self._update_progress(pkg_name, 'FAILED', str(e))
            self.failed_packages.append(package_id)
            log_error(f"Error installing {pkg_name}: {e}")
            return False

    # ==========================================================
    # INSTALLATION PLAN
    # ==========================================================

    def execute_installation_plan(self, plan):

        total = len(plan)
        success_count = 0
        failed_count = 0

        for i, step in enumerate(plan, 1):

            log_info(f"Step {i}/{total}: Installing {step['name']}")

            if step['type'] == "python":

                success = self.install_python_package(
                    step['pip_name'],
                    step['description']
                )

            elif step['type'] == "system":

                success = self.install_system_package(
                    step['name'],
                    step['description']
                )

            else:

                success = False

            if success:
                success_count += 1
            else:
                failed_count += 1

            time.sleep(0.5)

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "installed": self.installed_packages,
            "failed_list": self.failed_packages
        }

    # ==========================================================
    # DIRECTORY SETUP
    # ==========================================================

    def setup_directories(self):

        from Installer.utils import ensure_directory

        self._update_progress("directories", "INSTALLING", "Creating directory structure...")

        directories = [
            "./Captures",
            "./installation_logs",
            "./assets",
            "./views"
        ]

        for d in directories:
            ensure_directory(d)

        self._update_progress("directories", "SUCCESS", "Directories ready")

    # ==========================================================
    # SURICATA SETUP
    # ==========================================================

    def setup_suricata_rules(self):
        """
        Configure Suricata integration for DropGuard
        """

        self._update_progress("suricata_rules", "INSTALLING", "Configuring Suricata for DropGuard...")

        rules_dir = "/var/lib/suricata/rules"
        local_rules = f"{rules_dir}/local.rules"
        dropguard_rules = f"{rules_dir}/dropguard.rules"

        dropguard_config = "/etc/suricata/dropguard.yaml"
        suricata_yaml = "/etc/suricata/suricata.yaml"

        try:

            if not is_root():
                log_warning("Root required for Suricata configuration")
                return False

            subprocess.run(["mkdir", "-p", rules_dir], check=True)

            if not os.path.exists(local_rules):
                subprocess.run(["touch", local_rules], check=True)

            subprocess.run(["chmod", "644", local_rules], check=True)

            # ---------------------------------------------------
            # Create DropGuard rules file
            # ---------------------------------------------------

            if not os.path.exists(dropguard_rules):

                subprocess.run(["touch", dropguard_rules], check=True)
                subprocess.run(["chmod", "644", dropguard_rules], check=True)

                log_info("Created dropguard.rules")

            # ---------------------------------------------------
            # Create DropGuard config
            # ---------------------------------------------------

            if not os.path.exists(dropguard_config):

                config = """vars:
                address-groups:
                HOME_NET: "[192.168.0.0/16]"
                default-rule-path: /var/lib/suricata/rules
                rule-files:
                - dropguard.rules"""

                with open(dropguard_config, "w") as f:
                    f.write(config)

                subprocess.run(["chmod", "644", dropguard_config], check=True)

                log_info("Created dropguard.yaml")

            # ---------------------------------------------------
            # Ensure Suricata loads DropGuard config
            # ---------------------------------------------------

            include_line = "include: /etc/suricata/dropguard.yaml"

            if os.path.exists(suricata_yaml):

                with open(suricata_yaml, "r") as f:
                    content = f.read()

                if include_line not in content:

                    with open(suricata_yaml, "a") as f:
                        f.write("\n" + include_line + "\n")

                    log_info("Added DropGuard include to suricata.yaml")

            self._update_progress("suricata_rules", "SUCCESS", "Suricata configured for DropGuard")

            return True

        except Exception as e:

            self._update_progress("suricata_rules", "FAILED", str(e))
            log_error(f"Suricata setup failed: {e}")
            return False