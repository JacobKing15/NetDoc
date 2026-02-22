"""Menu-driven CLI interface for the Network Documentation Generator."""

from __future__ import annotations

import ipaddress  # FIX [REVIEW 1.6]: stdlib IP validation, no new dependency
import json       # FIX [REVIEW 2.5]: needed to catch JSONDecodeError in run()
import re
from pathlib import Path

from rich.console import Console
from rich.markup import escape  # FIX [REVIEW 1.7]: escape user strings before Rich markup
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich import box

from modules.export import export_markdown, export_html

from modules.data import (
    NetworkData,
    Vlan,
    Server,
    Switch,
    DhcpScope,
    load_data,
    save_data,
    find_entry_index,
    add_vlan,
    update_vlan,
    delete_vlan,
    list_vlans,
    add_server,
    update_server,
    delete_server,
    list_servers,
    add_switch,
    update_switch,
    delete_switch,
    list_switches,
    add_dhcp_scope,
    update_dhcp_scope,
    delete_dhcp_scope,
    list_dhcp_scopes,
)

console = Console()

# ---------------------------------------------------------------------------
# Credential detection
# ---------------------------------------------------------------------------

# FIX [REVIEW 5.1]: Extended keyword list to cover network-specific credential
# patterns that were absent from the original set: SNMP community strings
# (community), WPA2/VPN pre-shared keys (preshared, psk), SSH passphrases
# (passphrase), Cisco enable passwords (enable), and bare token values (token).
_CREDENTIAL_KEYWORDS = re.compile(
    r"\b(password|passwd|secret|credential|api[_\-]?key|auth[_\-]?token|private[_\-]?key"
    r"|community|preshared|psk|passphrase|enable|token)\b",
    re.IGNORECASE,
)


def looks_like_credential(value: str) -> bool:
    """Return True if value matches known credential keywords or resembles a strong password.

    Detection uses two signals:
    - Explicit keywords such as 'password', 'secret', 'api_key', etc.
    - Heuristic: 8+ character string that contains all four character classes
      (uppercase, lowercase, digit, special symbol), typical of generated passwords.
    """
    if _CREDENTIAL_KEYWORDS.search(value):
        return True

    if len(value) >= 8:
        has_upper = bool(re.search(r"[A-Z]", value))
        has_lower = bool(re.search(r"[a-z]", value))
        has_digit = bool(re.search(r"\d", value))
        has_special = bool(re.search(r"[!@#$%^&*=+;'\",<>?\\|`~]", value))
        if all([has_upper, has_lower, has_digit, has_special]):
            return True

    return False


def _warn_credential() -> None:
    """Print a credential-storage warning to the console."""
    console.print(
        "\n[bold red]WARNING:[/bold red] That input looks like a password or credential.\n"
        "[yellow]Credentials must be stored in a dedicated password manager, not here.\n"
        "Please enter a different value.[/yellow]\n"
    )


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def safe_prompt(label: str, default: str = "") -> str:
    """Prompt for a string value, rejecting anything that looks like a credential.

    Loops until the user provides an acceptable value.
    """
    while True:
        value = Prompt.ask(label, default=default) if default else Prompt.ask(label)
        if looks_like_credential(value):
            _warn_credential()
            continue
        return value


def safe_edit_prompt(label: str, current: str) -> str:
    """Prompt to edit a string field.

    Keeps the current value when the user presses Enter.
    Rejects credential-like new values.
    """
    while True:
        value = Prompt.ask(label, default=current)
        if value == current:
            return value  # unchanged — skip credential check
        if looks_like_credential(value):
            _warn_credential()
            continue
        return value


# FIX [REVIEW 2.1]: Changed return type from Optional[int] to int | None
# (idiomatic Python 3.10+ style; from __future__ import annotations is active).
def pick_entry(count: int, noun: str = "entry") -> int | None:
    """Display a selection prompt and return a 0-based index, or None if cancelled.

    Args:
        count: Total number of listed items.
        noun:  Human-readable label used in the prompt text.
    """
    console.print("  Enter [bold]0[/bold] to cancel.\n")
    while True:
        choice = IntPrompt.ask(f"  Select {noun} number")
        if choice == 0:
            return None
        if 1 <= choice <= count:
            return choice - 1
        console.print(f"[red]  Please enter a number between 1 and {count}, or 0 to cancel.[/red]")


def _menu(title: str, options: list[str]) -> int:
    """Render a numbered menu and return the chosen option number (1-based).

    Args:
        title:   Section heading displayed above the options.
        options: List of option labels in display order.
    """
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.rule(style="cyan")
    for i, opt in enumerate(options, 1):
        console.print(f"  [bold]{i}.[/bold] {opt}")
    console.print()
    while True:
        choice = IntPrompt.ask("  Select option")
        if 1 <= choice <= len(options):
            return choice
        console.print(f"[red]  Enter a number between 1 and {len(options)}.[/red]")


# ---------------------------------------------------------------------------
# IP validation helper
# ---------------------------------------------------------------------------

# FIX [REVIEW 1.6]: Lightweight IP validation using stdlib ipaddress module.
# Accepts any valid IPv4 or IPv6 address; no new dependency required.
def is_valid_ip(value: str) -> bool:
    """Return True if value is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Table display helpers
# ---------------------------------------------------------------------------

def show_vlan_table(vlans: list[Vlan]) -> None:
    """Render a Rich table of VLAN entries, numbered from 1."""
    if not vlans:
        console.print("[dim]  No VLANs on record.[/dim]")
        return
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Name", min_width=16)
    table.add_column("Subnet", min_width=18)
    table.add_column("Purpose")
    for i, v in enumerate(vlans, 1):
        table.add_row(str(i), str(v["id"]), v["name"], v["subnet"], v["purpose"])
    console.print(table)


def show_server_table(servers: list[Server]) -> None:
    """Render a Rich table of server entries, numbered from 1."""
    if not servers:
        console.print("[dim]  No servers on record.[/dim]")
        return
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Hostname", style="cyan", min_width=18)
    table.add_column("IP Address", min_width=15)
    table.add_column("Role", min_width=14)
    table.add_column("Location")
    for i, s in enumerate(servers, 1):
        table.add_row(str(i), s["hostname"], s["ip"], s["role"], s["location"])
    console.print(table)


def show_switch_table(switches: list[Switch]) -> None:
    """Render a Rich table of switch entries, numbered from 1."""
    if not switches:
        console.print("[dim]  No switches on record.[/dim]")
        return
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="cyan", min_width=18)
    table.add_column("IP Address", min_width=15)
    table.add_column("Location", min_width=14)
    table.add_column("Uplink")
    for i, s in enumerate(switches, 1):
        table.add_row(str(i), s["name"], s["ip"], s["location"], s["uplink"])
    console.print(table)


def show_dhcp_table(scopes: list[DhcpScope]) -> None:
    """Render a Rich table of DHCP scope entries, numbered from 1."""
    if not scopes:
        console.print("[dim]  No DHCP scopes on record.[/dim]")
        return
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="cyan", min_width=18)
    table.add_column("Range", min_width=22)
    table.add_column("Gateway", min_width=15)
    table.add_column("DNS")
    for i, s in enumerate(scopes, 1):
        table.add_row(str(i), s["name"], s["range"], s["gateway"], s["dns"])
    console.print(table)


# ---------------------------------------------------------------------------
# New-entry prompt helpers
# ---------------------------------------------------------------------------

def prompt_new_vlan() -> Vlan:
    """Collect fields for a brand-new VLAN entry from the user."""
    console.print("\n[bold]New VLAN[/bold]")
    # FIX [REVIEW 1.5]: Enforce the 1–4094 valid VLAN ID range after IntPrompt,
    # which only guarantees an integer but not the network-standard range.
    while True:
        vlan_id = IntPrompt.ask("  VLAN ID (1–4094)")
        if 1 <= vlan_id <= 4094:
            break
        console.print("[red]  VLAN ID must be between 1 and 4094.[/red]")
    name = safe_prompt("  Name")
    subnet = safe_prompt("  Subnet (e.g. 10.0.10.0/24)")
    purpose = safe_prompt("  Purpose")
    return Vlan(id=vlan_id, name=name, subnet=subnet, purpose=purpose)


def prompt_new_server() -> Server:
    """Collect fields for a brand-new server entry from the user."""
    console.print("\n[bold]New Server[/bold]")
    hostname = safe_prompt("  Hostname")
    # FIX [REVIEW 1.6]: Validate IP address format using stdlib ipaddress so
    # typos like '10.0.1' or '10.0.1.999' are caught before saving.
    while True:
        ip = safe_prompt("  IP address")
        if is_valid_ip(ip):
            break
        console.print("[red]  Please enter a valid IPv4 or IPv6 address (e.g. 10.0.1.5).[/red]")
    role = safe_prompt("  Role (e.g. web, db, backup)")
    location = safe_prompt("  Location (e.g. Rack A1, Cloud)")
    return Server(hostname=hostname, ip=ip, role=role, location=location)


def prompt_new_switch() -> Switch:
    """Collect fields for a brand-new switch entry from the user."""
    console.print("\n[bold]New Switch[/bold]")
    name = safe_prompt("  Name")
    # FIX [REVIEW 1.6]: Validate IP address format (same as server IP).
    while True:
        ip = safe_prompt("  IP address")
        if is_valid_ip(ip):
            break
        console.print("[red]  Please enter a valid IPv4 or IPv6 address (e.g. 10.0.1.1).[/red]")
    location = safe_prompt("  Location")
    uplink = safe_prompt("  Uplink (e.g. ge-0/0/0 to core-sw-01)")
    return Switch(name=name, ip=ip, location=location, uplink=uplink)


def prompt_new_dhcp_scope() -> DhcpScope:
    """Collect fields for a brand-new DHCP scope entry from the user."""
    console.print("\n[bold]New DHCP Scope[/bold]")
    name = safe_prompt("  Name")
    ip_range = safe_prompt("  Range (e.g. 10.0.10.100-10.0.10.200)")
    # FIX [REVIEW 1.6]: Validate gateway as a single IP address.
    while True:
        gateway = safe_prompt("  Gateway")
        if is_valid_ip(gateway):
            break
        console.print("[red]  Please enter a valid IPv4 or IPv6 address (e.g. 10.0.10.1).[/red]")
    # FIX [REVIEW 1.6]: Validate DNS — accepts one or more comma/space-separated
    # IP addresses to support redundant DNS configurations (e.g. "8.8.8.8, 1.1.1.1").
    while True:
        dns = safe_prompt("  DNS server(s)")
        parts = [p.strip() for p in dns.replace(",", " ").split() if p.strip()]
        if parts and all(is_valid_ip(p) for p in parts):
            break
        console.print(
            "[red]  Please enter valid IPv4/IPv6 address(es) "
            "(e.g. 8.8.8.8 or 8.8.8.8, 1.1.1.1).[/red]"
        )
    return DhcpScope(name=name, range=ip_range, gateway=gateway, dns=dns)


# ---------------------------------------------------------------------------
# Edit-entry prompt helpers
# ---------------------------------------------------------------------------

def prompt_edit_vlan(current: Vlan) -> dict:
    """Prompt the user to update VLAN fields; pressing Enter keeps the current value."""
    console.print("\n[bold]Edit VLAN[/bold]  [dim](press Enter to keep current value)[/dim]")
    new_id = IntPrompt.ask("  VLAN ID", default=current["id"])
    name = safe_edit_prompt("  Name", current["name"])
    subnet = safe_edit_prompt("  Subnet", current["subnet"])
    purpose = safe_edit_prompt("  Purpose", current["purpose"])
    return {"id": new_id, "name": name, "subnet": subnet, "purpose": purpose}


def prompt_edit_server(current: Server) -> dict:
    """Prompt the user to update server fields; pressing Enter keeps the current value."""
    console.print("\n[bold]Edit Server[/bold]  [dim](press Enter to keep current value)[/dim]")
    hostname = safe_edit_prompt("  Hostname", current["hostname"])
    ip = safe_edit_prompt("  IP address", current["ip"])
    role = safe_edit_prompt("  Role", current["role"])
    location = safe_edit_prompt("  Location", current["location"])
    return {"hostname": hostname, "ip": ip, "role": role, "location": location}


def prompt_edit_switch(current: Switch) -> dict:
    """Prompt the user to update switch fields; pressing Enter keeps the current value."""
    console.print("\n[bold]Edit Switch[/bold]  [dim](press Enter to keep current value)[/dim]")
    name = safe_edit_prompt("  Name", current["name"])
    ip = safe_edit_prompt("  IP address", current["ip"])
    location = safe_edit_prompt("  Location", current["location"])
    uplink = safe_edit_prompt("  Uplink", current["uplink"])
    return {"name": name, "ip": ip, "location": location, "uplink": uplink}


def prompt_edit_dhcp_scope(current: DhcpScope) -> dict:
    """Prompt the user to update DHCP scope fields; pressing Enter keeps the current value."""
    console.print("\n[bold]Edit DHCP Scope[/bold]  [dim](press Enter to keep current value)[/dim]")
    name = safe_edit_prompt("  Name", current["name"])
    ip_range = safe_edit_prompt("  Range", current["range"])
    gateway = safe_edit_prompt("  Gateway", current["gateway"])
    dns = safe_edit_prompt("  DNS", current["dns"])
    return {"name": name, "range": ip_range, "gateway": gateway, "dns": dns}


# ---------------------------------------------------------------------------
# VLAN actions
# ---------------------------------------------------------------------------

def action_list_vlans(data: NetworkData) -> None:
    """Display all VLANs in a formatted table."""
    console.print("\n[bold cyan]VLANs[/bold cyan]")
    show_vlan_table(list_vlans(data))


def action_add_vlan(data: NetworkData) -> None:
    """Prompt for a new VLAN, add it to the dataset, and save."""
    vlan = prompt_new_vlan()
    try:
        add_vlan(data, vlan)
        save_data(data)
        console.print(f"[green]  VLAN {vlan['id']} added.[/green]")
    except ValueError as exc:
        console.print(f"[red]  Error: {exc}[/red]")


def action_edit_vlan(data: NetworkData) -> None:
    """Let the user pick a VLAN to edit, apply changes, and save."""
    vlans = list_vlans(data)
    if not vlans:
        console.print("[yellow]  No VLANs to edit.[/yellow]")
        return
    console.print("\n[bold cyan]Edit VLAN — select entry[/bold cyan]")
    show_vlan_table(vlans)
    idx_sorted = pick_entry(len(vlans), "VLAN")
    if idx_sorted is None:
        return
    selected = vlans[idx_sorted]
    updates = prompt_edit_vlan(selected)

    # Guard: reject ID change that would collide with another existing VLAN
    if updates["id"] != selected["id"] and any(
        v["id"] == updates["id"] for v in data["vlans"]
    ):
        console.print(f"[red]  Error: VLAN {updates['id']} already exists.[/red]")
        return

    real_idx = find_entry_index(data["vlans"], "id", selected["id"])
    # FIX [REVIEW 3.1]: Guard against find_entry_index returning None.
    # Under normal use this cannot happen, but if the data file is externally
    # modified between the listing and the write, real_idx would be None and
    # data["vlans"][None] would raise an unhelpful TypeError.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    update_vlan(data, real_idx, updates)
    save_data(data)
    console.print("[green]  VLAN updated.[/green]")


def action_delete_vlan(data: NetworkData) -> None:
    """Let the user pick a VLAN to delete, confirm, and save."""
    vlans = list_vlans(data)
    if not vlans:
        console.print("[yellow]  No VLANs to delete.[/yellow]")
        return
    console.print("\n[bold cyan]Delete VLAN — select entry[/bold cyan]")
    show_vlan_table(vlans)
    idx_sorted = pick_entry(len(vlans), "VLAN")
    if idx_sorted is None:
        return
    selected = vlans[idx_sorted]
    # FIX [REVIEW 1.7]: Escape user-supplied name before interpolating into Rich
    # markup; a name containing e.g. '[bold red]' would otherwise be rendered.
    if not Confirm.ask(f"  Delete VLAN {selected['id']} ({escape(selected['name'])})?"):
        return
    real_idx = find_entry_index(data["vlans"], "id", selected["id"])
    # FIX [REVIEW 3.1]: Guard against None index (see action_edit_vlan for rationale).
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    delete_vlan(data, real_idx)
    save_data(data)
    console.print("[green]  VLAN deleted.[/green]")


# ---------------------------------------------------------------------------
# Server actions
# ---------------------------------------------------------------------------

def action_list_servers(data: NetworkData) -> None:
    """Display all servers in a formatted table."""
    console.print("\n[bold cyan]Servers[/bold cyan]")
    show_server_table(list_servers(data))


def action_add_server(data: NetworkData) -> None:
    """Prompt for a new server, add it to the dataset, and save."""
    server = prompt_new_server()
    try:
        add_server(data, server)
        save_data(data)
        # FIX [REVIEW 1.7]: Escape hostname in Rich markup string.
        console.print(f"[green]  Server '{escape(server['hostname'])}' added.[/green]")
    except ValueError as exc:
        console.print(f"[red]  Error: {exc}[/red]")


def action_edit_server(data: NetworkData) -> None:
    """Let the user pick a server to edit, apply changes, and save."""
    servers = list_servers(data)
    if not servers:
        console.print("[yellow]  No servers to edit.[/yellow]")
        return
    console.print("\n[bold cyan]Edit Server — select entry[/bold cyan]")
    show_server_table(servers)
    idx_sorted = pick_entry(len(servers), "server")
    if idx_sorted is None:
        return
    selected = servers[idx_sorted]
    updates = prompt_edit_server(selected)

    if updates["hostname"] != selected["hostname"] and any(
        s["hostname"] == updates["hostname"] for s in data["servers"]
    ):
        # FIX [REVIEW 1.7]: Escape hostname in Rich markup string.
        console.print(f"[red]  Error: Server '{escape(updates['hostname'])}' already exists.[/red]")
        return

    real_idx = find_entry_index(data["servers"], "hostname", selected["hostname"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    update_server(data, real_idx, updates)
    save_data(data)
    console.print("[green]  Server updated.[/green]")


def action_delete_server(data: NetworkData) -> None:
    """Let the user pick a server to delete, confirm, and save."""
    servers = list_servers(data)
    if not servers:
        console.print("[yellow]  No servers to delete.[/yellow]")
        return
    console.print("\n[bold cyan]Delete Server — select entry[/bold cyan]")
    show_server_table(servers)
    idx_sorted = pick_entry(len(servers), "server")
    if idx_sorted is None:
        return
    selected = servers[idx_sorted]
    # FIX [REVIEW 1.7]: Escape hostname before interpolating into Rich markup.
    if not Confirm.ask(f"  Delete server '{escape(selected['hostname'])}'?"):
        return
    real_idx = find_entry_index(data["servers"], "hostname", selected["hostname"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    delete_server(data, real_idx)
    save_data(data)
    console.print("[green]  Server deleted.[/green]")


# ---------------------------------------------------------------------------
# Switch actions
# ---------------------------------------------------------------------------

def action_list_switches(data: NetworkData) -> None:
    """Display all switches in a formatted table."""
    console.print("\n[bold cyan]Switches[/bold cyan]")
    show_switch_table(list_switches(data))


def action_add_switch(data: NetworkData) -> None:
    """Prompt for a new switch, add it to the dataset, and save."""
    switch = prompt_new_switch()
    try:
        add_switch(data, switch)
        save_data(data)
        # FIX [REVIEW 1.7]: Escape switch name in Rich markup string.
        console.print(f"[green]  Switch '{escape(switch['name'])}' added.[/green]")
    except ValueError as exc:
        console.print(f"[red]  Error: {exc}[/red]")


def action_edit_switch(data: NetworkData) -> None:
    """Let the user pick a switch to edit, apply changes, and save."""
    switches = list_switches(data)
    if not switches:
        console.print("[yellow]  No switches to edit.[/yellow]")
        return
    console.print("\n[bold cyan]Edit Switch — select entry[/bold cyan]")
    show_switch_table(switches)
    idx_sorted = pick_entry(len(switches), "switch")
    if idx_sorted is None:
        return
    selected = switches[idx_sorted]
    updates = prompt_edit_switch(selected)

    if updates["name"] != selected["name"] and any(
        s["name"] == updates["name"] for s in data["switches"]
    ):
        # FIX [REVIEW 1.7]: Escape name in Rich markup string.
        console.print(f"[red]  Error: Switch '{escape(updates['name'])}' already exists.[/red]")
        return

    real_idx = find_entry_index(data["switches"], "name", selected["name"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    update_switch(data, real_idx, updates)
    save_data(data)
    console.print("[green]  Switch updated.[/green]")


def action_delete_switch(data: NetworkData) -> None:
    """Let the user pick a switch to delete, confirm, and save."""
    switches = list_switches(data)
    if not switches:
        console.print("[yellow]  No switches to delete.[/yellow]")
        return
    console.print("\n[bold cyan]Delete Switch — select entry[/bold cyan]")
    show_switch_table(switches)
    idx_sorted = pick_entry(len(switches), "switch")
    if idx_sorted is None:
        return
    selected = switches[idx_sorted]
    # FIX [REVIEW 1.7]: Escape switch name before interpolating into Rich markup.
    if not Confirm.ask(f"  Delete switch '{escape(selected['name'])}'?"):
        return
    real_idx = find_entry_index(data["switches"], "name", selected["name"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    delete_switch(data, real_idx)
    save_data(data)
    console.print("[green]  Switch deleted.[/green]")


# ---------------------------------------------------------------------------
# DHCP Scope actions
# ---------------------------------------------------------------------------

def action_list_dhcp_scopes(data: NetworkData) -> None:
    """Display all DHCP scopes in a formatted table."""
    console.print("\n[bold cyan]DHCP Scopes[/bold cyan]")
    show_dhcp_table(list_dhcp_scopes(data))


def action_add_dhcp_scope(data: NetworkData) -> None:
    """Prompt for a new DHCP scope, add it to the dataset, and save."""
    scope = prompt_new_dhcp_scope()
    try:
        add_dhcp_scope(data, scope)
        save_data(data)
        # FIX [REVIEW 1.7]: Escape scope name in Rich markup string.
        console.print(f"[green]  DHCP scope '{escape(scope['name'])}' added.[/green]")
    except ValueError as exc:
        console.print(f"[red]  Error: {exc}[/red]")


def action_edit_dhcp_scope(data: NetworkData) -> None:
    """Let the user pick a DHCP scope to edit, apply changes, and save."""
    scopes = list_dhcp_scopes(data)
    if not scopes:
        console.print("[yellow]  No DHCP scopes to edit.[/yellow]")
        return
    console.print("\n[bold cyan]Edit DHCP Scope — select entry[/bold cyan]")
    show_dhcp_table(scopes)
    idx_sorted = pick_entry(len(scopes), "scope")
    if idx_sorted is None:
        return
    selected = scopes[idx_sorted]
    updates = prompt_edit_dhcp_scope(selected)

    if updates["name"] != selected["name"] and any(
        s["name"] == updates["name"] for s in data["dhcp_scopes"]
    ):
        # FIX [REVIEW 1.7]: Escape scope name in Rich markup string.
        console.print(f"[red]  Error: DHCP scope '{escape(updates['name'])}' already exists.[/red]")
        return

    real_idx = find_entry_index(data["dhcp_scopes"], "name", selected["name"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    update_dhcp_scope(data, real_idx, updates)
    save_data(data)
    console.print("[green]  DHCP scope updated.[/green]")


def action_delete_dhcp_scope(data: NetworkData) -> None:
    """Let the user pick a DHCP scope to delete, confirm, and save."""
    scopes = list_dhcp_scopes(data)
    if not scopes:
        console.print("[yellow]  No DHCP scopes to delete.[/yellow]")
        return
    console.print("\n[bold cyan]Delete DHCP Scope — select entry[/bold cyan]")
    show_dhcp_table(scopes)
    idx_sorted = pick_entry(len(scopes), "scope")
    if idx_sorted is None:
        return
    selected = scopes[idx_sorted]
    # FIX [REVIEW 1.7]: Escape scope name before interpolating into Rich markup.
    if not Confirm.ask(f"  Delete DHCP scope '{escape(selected['name'])}'?"):
        return
    real_idx = find_entry_index(data["dhcp_scopes"], "name", selected["name"])
    # FIX [REVIEW 3.1]: Guard against None index.
    if real_idx is None:
        console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
        return
    delete_dhcp_scope(data, real_idx)
    save_data(data)
    console.print("[green]  DHCP scope deleted.[/green]")


# ---------------------------------------------------------------------------
# Export action
# ---------------------------------------------------------------------------

# Root of the project is one level above this module file (modules/cli.py).
_PROJECT_ROOT = Path(__file__).parent.parent
_EXPORTS_DIR = _PROJECT_ROOT / "exports"


def action_export(data: NetworkData) -> None:
    """Export the current dataset to Markdown and HTML files in the exports/ folder.

    Creates the exports/ directory if it does not already exist, then writes
    both formats and prints the resolved paths of the generated files.
    """
    _EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path = str(_EXPORTS_DIR / "network_docs.md")
    html_path = str(_EXPORTS_DIR / "network_docs.html")

    try:
        export_markdown(data, md_path)
        export_html(data, html_path)
    except OSError as exc:
        console.print(f"[bold red]  Export failed:[/bold red] {exc}")
        return

    console.print("\n[bold green]  Export complete![/bold green]")
    console.print(f"  [cyan]Markdown:[/cyan] {md_path}")
    console.print(f"  [cyan]HTML:[/cyan]     {html_path}\n")


# ---------------------------------------------------------------------------
# Category menus
# ---------------------------------------------------------------------------

_CATEGORY_OPTIONS = ["List all", "Add new", "Edit existing", "Delete", "Back"]


def vlans_menu(data: NetworkData) -> None:
    """Display the VLANs sub-menu and dispatch to the chosen action."""
    actions = {
        1: action_list_vlans,
        2: action_add_vlan,
        3: action_edit_vlan,
        4: action_delete_vlan,
    }
    while True:
        choice = _menu("VLANs", _CATEGORY_OPTIONS)
        if choice == 5:
            return
        actions[choice](data)


def servers_menu(data: NetworkData) -> None:
    """Display the Servers sub-menu and dispatch to the chosen action."""
    actions = {
        1: action_list_servers,
        2: action_add_server,
        3: action_edit_server,
        4: action_delete_server,
    }
    while True:
        choice = _menu("Servers", _CATEGORY_OPTIONS)
        if choice == 5:
            return
        actions[choice](data)


def switches_menu(data: NetworkData) -> None:
    """Display the Switches sub-menu and dispatch to the chosen action."""
    actions = {
        1: action_list_switches,
        2: action_add_switch,
        3: action_edit_switch,
        4: action_delete_switch,
    }
    while True:
        choice = _menu("Switches", _CATEGORY_OPTIONS)
        if choice == 5:
            return
        actions[choice](data)


def dhcp_scopes_menu(data: NetworkData) -> None:
    """Display the DHCP Scopes sub-menu and dispatch to the chosen action."""
    actions = {
        1: action_list_dhcp_scopes,
        2: action_add_dhcp_scope,
        3: action_edit_dhcp_scope,
        4: action_delete_dhcp_scope,
    }
    while True:
        choice = _menu("DHCP Scopes", _CATEGORY_OPTIONS)
        if choice == 5:
            return
        actions[choice](data)


# ---------------------------------------------------------------------------
# Main menu and entry point
# ---------------------------------------------------------------------------

_MAIN_OPTIONS = ["VLANs", "Servers", "Switches", "DHCP Scopes", "Export Documentation", "Quit"]


def main_menu(data: NetworkData) -> None:
    """Run the top-level menu loop, routing to each category sub-menu."""
    menus = {
        1: vlans_menu,
        2: servers_menu,
        3: switches_menu,
        4: dhcp_scopes_menu,
        5: action_export,
    }
    while True:
        choice = _menu("Main Menu", _MAIN_OPTIONS)
        if choice == 6:
            console.print("\n[dim]Goodbye.[/dim]\n")
            return
        menus[choice](data)


def run() -> None:
    """Load persisted data and enter the main menu loop."""
    console.print(
        Panel.fit(
            "[bold cyan]Network Documentation Generator[/bold cyan]",
            border_style="cyan",
            padding=(0, 4),
        )
    )
    # FIX [REVIEW 2.5]: Catch startup exceptions from load_data() and display a
    # human-readable message instead of propagating a raw traceback to the user.
    # JSONDecodeError (corrupt file), OSError (permission/disk), and ValueError
    # (schema validation failure) are all surfaces here with actionable guidance.
    try:
        data = load_data()
    except json.JSONDecodeError as exc:
        console.print(f"\n[bold red]Cannot start:[/bold red] {exc}")
        return
    except (OSError, ValueError) as exc:
        console.print(f"\n[bold red]Cannot start:[/bold red] {exc}")
        return
    main_menu(data)
