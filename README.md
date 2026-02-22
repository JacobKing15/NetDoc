# NetDoc

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**Network documentation that actually stays current.**

NetDoc is a menu-driven CLI tool built for IT teams that need structured, exportable documentation of their network infrastructure — VLANs, servers, switches, and DHCP scopes — without the overhead of an enterprise platform or the chaos of a shared spreadsheet.

It runs anywhere Python runs, requires no database, and exports clean markdown and HTML that can live in a wiki, a shared drive, or a Git repository.

---

## Why It Exists

Most network documentation lives in a decade-old spreadsheet nobody fully trusts, a wiki page that hasn't been touched since the last sysadmin left, or someone's head. NetDoc fixes that by making it fast to record infrastructure details and painless to export them into formats that anyone on the team can read.

---

## Features

- **Structured data entry** for VLANs, servers, switches, and DHCP scopes
- **Menu-driven CLI** — no flags to memorize, no RTFM required
- **Dual export targets** — markdown (`.md`) for Git/wikis, HTML for local viewing or printing
- **Rich terminal output** using the `rich` library — color-coded tables, clean prompts
- **Intentionally credential-free** — see [Security Note](#security-note)
- **No database required** — data stored in structured JSON flat files
- **Fully testable** — pytest test suite included

---

## Requirements

- Python 3.10 or higher
- [`rich`](https://github.com/Textualize/rich) — terminal formatting
- [`pytest`](https://docs.pytest.org/) — for running the test suite

---

## Installation

```bash
git clone https://github.com/your-org/netdoc.git
cd netdoc
pip install -r requirements.txt
python main.py
```

No virtual environment is required, but one is recommended if you're running multiple Python projects on the same machine:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Usage

NetDoc opens to a main menu. All navigation is number-based — no commands to remember.

```
╔══════════════════════════════════════╗
║          NetDoc — Main Menu          ║
╚══════════════════════════════════════╝

 [1] VLANs
 [2] Servers
 [3] Switches
 [4] DHCP Scopes
 [5] Export Documentation
 [0] Exit

Select an option:
```

### Adding a VLAN

```
── VLAN Menu ──────────────────────────

 [1] View all VLANs
 [2] Add VLAN
 [3] Edit VLAN
 [4] Delete VLAN
 [0] Back

Select an option: 2

VLAN ID      : 20
Name         : Guest-Wireless
Description  : Guest Wi-Fi network, isolated from internal resources
Subnet       : 10.20.0.0/22
Gateway      : 10.20.0.1
Notes        : Isolated from corporate VLAN. No access to internal servers.

✔ VLAN 20 saved.
```

### Viewing Servers

```
┌──────────────────┬─────────────────┬──────────────┬──────────────────────┐
│ Hostname         │ IP Address      │ Role         │ OS                   │
├──────────────────┼─────────────────┼──────────────┼──────────────────────┤
│ dc01             │ 10.10.1.10      │ Domain Ctrl  │ Windows Server 2022  │
│ dc02             │ 10.10.1.11      │ Domain Ctrl  │ Windows Server 2022  │
│ filesvr01        │ 10.10.1.20      │ File Server  │ Windows Server 2019  │
│ syslog01         │ 10.10.1.50      │ Syslog       │ Ubuntu 22.04 LTS     │
│ backup01         │ 10.10.1.60      │ Backup       │ Ubuntu 22.04 LTS     │
└──────────────────┴─────────────────┴──────────────┴──────────────────────┘
```

### Exporting

```
── Export Documentation ───────────────

 [1] Export as Markdown
 [2] Export as HTML
 [3] Export both
 [0] Back

Select an option: 3

Output directory [./export]:

✔ Markdown exported → export/network_docs.md
✔ HTML exported     → export/network_docs.html
```

---

## Export Example

The markdown export is structured for readability and easy inclusion in a wiki or Git repository:

```markdown
# Network Documentation
Generated: 2026-02-21

---

## VLANs

| VLAN ID | Name             | Subnet        | Gateway    |
|---------|------------------|---------------|------------|
| 10      | Corp-Wired       | 10.10.0.0/23  | 10.10.0.1  |
| 20      | Guest-Wireless   | 10.20.0.0/22  | 10.20.0.1  |
| 30      | VoIP             | 10.30.0.0/24  | 10.30.0.1  |
| 99      | Management       | 10.99.0.0/24  | 10.99.0.1  |

---

## Servers

| Hostname   | IP Address  | Role         | OS                  |
|------------|-------------|--------------|---------------------|
| dc01       | 10.10.1.10  | Domain Ctrl  | Windows Server 2022 |
| syslog01   | 10.10.1.50  | Syslog       | Ubuntu 22.04 LTS    |

---

## DHCP Scopes

| Scope Name       | Range Start  | Range End      | Lease Time |
|------------------|--------------|----------------|------------|
| Guest-Wireless   | 10.20.1.0    | 10.20.3.254    | 4 hours    |
| Corp-Wired       | 10.10.0.50   | 10.10.1.200    | 8 hours    |
```

The HTML export uses the same structure with inline styles — no external dependencies, suitable for printing or sharing directly.

---

## Running Tests

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

Tests cover data validation, export formatting, and menu routing logic.

---

## Security Note

**NetDoc does not store, prompt for, or export credentials of any kind.**

This is intentional. Device passwords, SNMP community strings, service account credentials, and API keys have no place in a documentation tool — especially one whose output may end up in a shared wiki or repository.

For credential management, the IT team should use a dedicated secrets manager:

- **[Bitwarden](https://bitwarden.com/)** — open source, self-hostable, team-friendly
- **[KeePass](https://keepass.info/)** — offline, file-based, works well in air-gapped environments

If you need to document that a device *has* credentials stored in a particular vault, a notes field is available in the server and switch records for exactly that kind of reference (e.g., `"Credentials in Bitwarden — 'Core Switches' collection"`).

---

## Contributing

This tool was built to solve a real problem. If you're managing network infrastructure and have a feature that would make it more useful, contributions are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Write tests for your changes
4. Submit a pull request with a clear description of what you changed and why

Bug reports and feature requests can be filed as GitHub Issues.

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

This tool is provided as-is. It is not affiliated with any network vendor or software company.
