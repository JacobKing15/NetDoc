---
skipPermissions: true
---
# NetDoc - Network Documentation Generator

## Project Overview
A Python CLI tool for IT administrators to manage and export network
documentation. Suitable for any team managing network infrastructure.

## Project Structure
network-doc-maker/
├── main.py
├── modules/
│   ├── cli.py
│   ├── data.py
│   └── export.py
├── data/
│   └── network.json
├── exports/
├── tests/
│   └── test_all.py
└── README.md

## Tech Stack
- Python 3.10+
- rich (CLI formatting)
- pytest (testing)

## Key Rules
- Never store credentials or passwords in any data file or export
- All file operations use the data/ directory
- All exports go to the exports/ directory
- Functions should be small and single-purpose
- All functions require docstrings and type hints

## Data Models
vlans: id, name, subnet, purpose
servers: hostname, ip, role, location
switches: name, ip, location, uplink
dhcp_scopes: name, range, gateway, dns