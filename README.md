# 🛡️ DropGuard  
### Network Intrusion Detection & Prevention System (NIDPS)

DropGuard is a modular **Network Intrusion Detection and Prevention System (NIDPS)** featuring both a graphical monitoring interface and a headless command-line engine.  

It performs real-time packet capture, layered detection, automated response, dynamic rule generation, and forensic artifact storage.

Developed as a cybersecurity capstone to demonstrate practical defensive engineering and IDS/IPS architecture.

---

## 🚀 Features

- Real-time packet sniffing using Scapy  
- Multi-stage detection pipeline  
- Event-driven internal architecture  
- Automatic MAC blacklisting  
- Dynamic Suricata-compatible rule generation  
- PCAP capture and export  
- Tkinter-based graphical monitoring interface  
- Headless CLI operation  
- Thread-safe backend engine  

---

## 🧱 High-Level Architecture

GUI / CLI  
Controller  
Event Bus  
Detection Pipeline  
Rule Engine – Threat Engine – Responders  
Storage Layer  

---

## 📂 Project Structure

DROPGUARD/
├── GUI_Monitor/
│   ├── assets/  
│   ├── Captures/  
│   ├── views/  
│   ├── controller.py  
│   ├── main.py  
│   ├── utils.py  
│   └── whitelist.txt  
│
├── nidps/
│   ├── core.py  
│   ├── sniffing.py  
│   ├── detection.py  
│   ├── detectors/  
│   ├── rules.py  
│   ├── responders.py  
│   ├── threats.py  
│   ├── events.py  
│   ├── storage.py  
│   └── main.py  
│
├── Installer/
└── README.md  

---

## 🔍 Detection Capabilities

- ARP Spoofing  
- Port Scanning  
- SSH attempts  
- FTP attempts  
- New host discovery  

---

## ⚡ Response Capabilities

- Generate alerts  
- Blacklist MAC addresses  
- Generate Suricata drop rules  
- Drop traffic  
- Log forensic artifacts  

---

## 🖥️ Running the GUI

python GUI_Monitor/main.py

## 📦 Dependencies

pip install scapy psutil

Linux:

sudo apt install tcpdump

---

## 🔐 Permissions

sudo python GUI_Monitor/main.py   

---

## 📜 License

Academic / Educational Use Only
