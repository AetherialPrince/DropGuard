from .dashboard import Dashboard
from .live_traffic import LiveTraffic
from .alerts import Alerts
from .whitelist import Whitelist
from .blacklist import Blacklist
from .suricata import Suricata
from .pcap import PCAP
from .custom_rules import CustomRulesPage
from .settings import Settings

PAGES={
"Dashboard":Dashboard,
"Live Traffic":LiveTraffic,
"Alerts":Alerts,
"Whitelist":Whitelist,
"Blacklist":Blacklist,
"Suricata Rules":Suricata,
"PCAP Manager":PCAP,
"Custom Rules":CustomRulesPage,
"Settings":Settings
}
