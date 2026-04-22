"""
main.py

Command-line entry point for launching the NIDPS engine
without the graphical interface.
"""

import sys
from nidps.core.core import start_nidps


# ===================== CLI ENTRY POINT ===================== #

if __name__ == "__main__":

    # Expect exactly one argument: network interface
    if len(sys.argv) != 2:
        print("Usage: python main.py <interface>")
        exit(1)

    interface = sys.argv[1]
    start_nidps(interface)