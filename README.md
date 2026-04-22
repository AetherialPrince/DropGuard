# DropGuard
**Network Intrusion Detection & Prevention System**
**Created by: Valentino Palacio, Jace Hillis and Marco Narvaez

DropGuard is a real-time network security monitor for Linux. It watches your local network for threats, alerts you when something suspicious is detected, and actively blocks malicious hosts — all through a graphical interface with no terminal required after installation.

---

## What It Detects

DropGuard ships with five built-in hardcoded detectors and a custom rule engine on top.

**New Host Discovery** — every time a device appears on the network for the first time, DropGuard logs its MAC and IP. By default this fires an alert only, no blocking.

**Port Scan Detection** — tracks how many unique destination ports a host contacts within a rolling time window. Once the threshold is crossed the host is alerted on, blacklisted, and a Suricata drop rule is generated automatically. Default: 10 ports in 30 seconds.

**SSH Attempt Detection** — any TCP packet destined for port 22 from an untrusted host triggers an alert, blacklists the source MAC, and writes a Suricata drop rule. Useful for catching lateral movement and brute-force setups early.

**FTP Attempt Detection** — same pipeline as SSH but for port 21. FTP sends credentials in plaintext so any attempt from an unknown host is treated as suspicious by default.

**ARP Spoof Detection** — detects when an attacker tries to poison the ARP cache to impersonate another host, most commonly the gateway. At startup DropGuard reads the router's MAC from the OS ARP cache (before sniffing begins, so an attacker cannot win a race condition) and pins it as the trusted baseline. Any ARP reply claiming the gateway IP with a different MAC triggers an immediate alert. For non-gateway IPs, repeated conflicting claims within a configurable window are required before alerting. Detected attackers are blacklisted and Suricata rules are written to drop their traffic.

**Custom Rules** — on top of the hardcoded detectors, you can define your own rules through the GUI matching on source IP, source MAC, destination IP, port, and protocol. Each rule independently controls whether it should alert, blacklist, or drop.

---

## How Responses Work

When a detector fires, DropGuard decides what to do based on the event type's **policy**. Each event type has four independent response actions:

| Action | What it does |
|---|---|
| **Alert** | Logs the event to the Alerts panel and database with timestamp, MAC, and IP |
| **Blacklist** | Adds the source MAC to the blacklist — all future traffic from that MAC is blocked |
| **Write Rule** | Generates a Suricata-compatible drop rule for the attacker's known IPs |
| **Drop** | Active packet dropping via Suricata and NFQUEUE at the kernel level |

Default policies out of the box:

| Event | Alert | Blacklist | Write Rule | Drop |
|---|---|---|---|---|
| New Host | ✓ | | | |
| Port Scan | ✓ | ✓ | ✓ | ✓ |
| SSH Attempt | ✓ | ✓ | ✓ | ✓ |
| FTP Attempt | ✓ | ✓ | ✓ | ✓ |
| ARP Spoof | ✓ | ✓ | ✓ | ✓ |

All policies are configurable through the Config file in the sourcecode, some within the settings page. 

---

## Requirements

- Debian-based Linux (Kali, Ubuntu, Linux Mint, etc.)
- Python 3.9 or later
- Suricata — installed automatically by the package
- Root access for packet sniffing and IPS enforcement

---

## Installation

Download the latest `dropguard_x.x_amd64.deb` from the [Releases](../../releases) page, then run:

```bash
sudo apt install ./dropguard_1.0_amd64.deb
```

apt resolves and installs Suricata automatically, places all project files, and runs post-install setup. When it finishes DropGuard is ready — no extra steps.

**Three ways to launch after installation:**

| Method | How |
|---|---|
| Applications menu | Search **DropGuard** under Network or Security |
| Desktop shortcut | Double-click the DropGuard icon on your Desktop |
| Terminal | Run `dropguard` from anywhere |

No terminal needs to stay open. Root privileges are handled silently by a sudoers rule the package installs.

### Uninstalling

```bash
# Remove the app, keep your config and logs
sudo apt remove dropguard

# Wipe everything including /opt/dropguard and logs
sudo apt purge dropguard
```

---

## Building from Source

```bash
git clone https://github.com/your-org/dropguard.git
cd dropguard
chmod +x build_deb.sh
./build_deb.sh
```

Produces `dropguard_1.0_amd64.deb` in the project root. Requires `dpkg-deb` (`sudo apt install dpkg`).

---

## User Guide

### Starting the Engine

Open DropGuard, select your network interface from the dropdown, and click **Start IDS**. The status indicator turns green and shows **PROTECTED**. Click **Stop IDS** to halt.

On startup DropGuard automatically whitelists your machine's MAC and your router's MAC so they are never treated as threats, regardless of what traffic they generate.

---

### Dashboard

The first page you see. Shows a live summary of:
- Total packets processed
- Total alerts fired
- Hosts discovered on the network
- Number of blacklisted and whitelisted devices

Also displays a live feed of the most recent alerts so you can spot threats at a glance without switching pages.

---

### Live Traffic

A real-time packet table showing every packet DropGuard processes:

| Column | Description |
|---|---|
| Timestamp | When the packet was seen |
| Source IP | Where the packet came from |
| Source MAC | Hardware address of the source |
| Protocol | ARP, TCP, UDP, etc. |
| Port | Destination port when applicable |
| Status | `PASS`, `WHITELISTED`, `ALERT`, or `DROP` |

---

### Alerts

The full alert log. Every detection event is recorded here with its timestamp, source MAC, source IP, and description of what was detected. Persists across restarts.

---

### Blacklist

Shows all discovered hosts on the left and the current blacklist on the right.

- **Add Selected** — select any host from the discovered list and block it immediately
- **Remove Selected** — unblock a host; the detection cooldown resets automatically so a resumed attack will be caught again from the first packet
- **Details panel** — clicking a blacklisted entry shows its full IP history, all alerts associated with it, and a log of every time it was blacklisted

---

### Whitelist

Shows all trusted hosts. Whitelisted MACs bypass the detection pipeline entirely and can never be blacklisted, even if traffic from them looks suspicious.

- **Add Selected** — trust a discovered host
- **Remove Selected** — revoke trust

Your own machine and router are added here automatically at startup.

---

### Custom Rules

Build detection rules without editing any config files. Each rule can match on any combination of:

- Source IP or MAC
- Destination IP
- Destination port
- Protocol (TCP, UDP, ICMP)

And independently trigger any of: **Alert**, **Blacklist**.

**Adding a rule** — fill in the form on the right side and click **Add Rule**. Source and destination support ANY, HOME (private IP ranges), an existing discovered host, or a custom IP/MAC.

**Editing a rule** — select it in the table and click **Edit Selected**. The form loads the rule's current values and the button switches to **Update Rule**. Click **Clear** to cancel.

**Deleting a rule** — select it and click **Delete Selected**.

---

### Suricata Rules

Displays the live contents of `/var/lib/suricata/rules/dropguard.rules` — the rule file Suricata uses for active packet dropping.

DropGuard writes to this file automatically when hosts are blacklisted, but you can also edit rules manually here. Click **Save & Reload** to write your changes and hot-reload Suricata without restarting anything.

---

### PCAP Manager

Shows the path to the most recent packet capture file. Captures are saved automatically on a configurable interval (default every 30 seconds while the engine is running). Open the file in Wireshark for forensic analysis.

---

### Settings

Fine-tune every aspect of DropGuard's behaviour without touching YAML files. All settings are searchable. Changed values are highlighted so you can see what differs from the defaults.

Key settings available:

| Setting | Default | What it controls |
|---|---|---|
| `detection.portscan.threshold` | 10 | Unique ports before flagging a scan |
| `detection.portscan.window` | 30s | Rolling window for port scan counting |
| `detection.arp_spoof.threshold` | 3 | Conflicting ARP claims before alerting |
| `detection.arp_spoof.window` | 15s | Window for ARP conflict tracking |
| `detection.arp_spoof.protect_gateway` | true | Immediate alert on any gateway MAC change |
| `detection.cooldown_seconds.PORT_SCAN` | 30s | Minimum gap between repeated port scan alerts for the same host |
| `detection.cooldown_seconds.SSH` | 60s | Same, for SSH alerts |
| `detection.cooldown_seconds.FTP` | 60s | Same, for FTP alerts |
| `detection.cooldown_seconds.ARP_SPOOF` | 180s | Same, for ARP spoof alerts |
| `features.ssh` | true | Enable/disable SSH detection entirely |
| `features.ftp` | true | Enable/disable FTP detection entirely |
| `features.portscan` | true | Enable/disable port scan detection |
| `features.arp_spoof` | true | Enable/disable ARP spoof detection |
| `features.discovery` | true | Enable/disable new host alerts |
| `pcap.interval` | 30s | How often capture files are written |
| `sniffer.threads` | 4 | Detection worker threads |

Click **Save** to apply, **Reset** to restore defaults, or **Reload** to re-read from disk.

---

## Project Structure

```
DropGuard/
├── GUI_Monitor/          # Tkinter GUI application
│   ├── main.py           # Entry point
│   ├── controller.py     # Startup, interface detection, event wiring
│   ├── bootstrap.py      # Suricata environment initialisation
│   ├── config.yaml       # User config overrides
│   ├── config_default.yaml  # Safe baseline defaults
│   ├── views/            # One file per GUI page
│   └── assets/           # Icons and images
├── nidps/                # Detection engine
│   ├── core/             # Sniffing loop and event bus
│   ├── detection/        # Packet pipeline, threat dispatch, responders
│   ├── detectors/        # ARP spoof, port scan, SSH/FTP, host discovery
│   ├── rules/            # Rule engine and custom rule matching
│   ├── storage/          # File and SQLite persistence
│   ├── suricata/         # Suricata config, runtime, and rule writer
│   └── config/           # YAML config loader
└── build_deb.sh          # Produces the installable .deb package
```

---

## License

Academic / Educational Use Only — Capstone Project
