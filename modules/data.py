"""Handles all JSON read/write operations for persistent network data storage."""

from __future__ import annotations

import json
import os
from pathlib import Path  # FIX [REVIEW 1.2, 1.3]: use pathlib for absolute path and atomic writes
from typing import Any, TypedDict  # FIX [REVIEW 2.1]: removed Optional (now using int | None)

# FIX [REVIEW 1.2]: Anchor DATA_FILE to this module's location so the tool
# works correctly regardless of the working directory it is launched from.
DATA_FILE: Path = Path(__file__).parent.parent / "data" / "network.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Vlan(TypedDict):
    """A single VLAN entry."""

    id: int
    name: str
    subnet: str
    purpose: str


class Server(TypedDict):
    """A single server entry."""

    hostname: str
    ip: str
    role: str
    location: str


class Switch(TypedDict):
    """A single network switch entry."""

    name: str
    ip: str
    location: str
    uplink: str


class DhcpScope(TypedDict):
    """A single DHCP scope entry."""

    name: str
    range: str
    gateway: str
    dns: str


class NetworkData(TypedDict):
    """Root structure that holds all four collections."""

    vlans: list[Vlan]
    servers: list[Server]
    switches: list[Switch]
    dhcp_scopes: list[DhcpScope]


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def _empty_data() -> NetworkData:
    """Return a freshly initialised empty NetworkData structure."""
    return {"vlans": [], "servers": [], "switches": [], "dhcp_scopes": []}


def load_data() -> NetworkData:
    """Load network data from JSON, returning an empty structure when the file is absent.

    Raises
    ------
    json.JSONDecodeError
        If the file exists but contains invalid JSON (e.g. truncated write).
    ValueError
        If the file exists and is valid JSON but does not have the expected
        top-level structure (missing required keys or wrong root type).
    """
    data_file = Path(DATA_FILE)  # handles both Path and str (monkeypatched in tests)
    if not data_file.exists():
        return _empty_data()

    # FIX [REVIEW 3.3]: Wrap json.load in try/except so a corrupt file surfaces
    # a clear message naming the file and suggesting recovery, rather than a
    # raw traceback.
    try:
        with open(data_file, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"network.json is corrupt or was truncated — {exc.msg}. "
            f"File: {data_file}. Restore from backup or delete the file to start fresh.",
            exc.doc,
            exc.pos,
        ) from exc

    # FIX [REVIEW 1.4]: Validate the loaded structure before returning it so
    # a manually edited file with the wrong shape fails loudly at load time
    # instead of causing a confusing KeyError or TypeError deep in CRUD code.
    if not isinstance(loaded, dict):
        raise ValueError(
            f"network.json has an invalid structure: root must be a JSON object, "
            f"got {type(loaded).__name__}. "
            f"File: {data_file}. Restore from backup or delete the file to start fresh."
        )
    required_keys = {"vlans", "servers", "switches", "dhcp_scopes"}
    missing = required_keys - loaded.keys()
    if missing:
        raise ValueError(
            f"network.json is missing required keys: {missing}. "
            f"File: {data_file}. Restore from backup or delete the file to start fresh."
        )

    return loaded


def save_data(data: NetworkData) -> None:
    """Persist network data to JSON, creating parent directories as needed.

    Uses an atomic write (temp file + os.replace) so a crash or
    KeyboardInterrupt mid-write cannot leave network.json corrupt.
    """
    data_file = Path(DATA_FILE)  # handles both Path and str (monkeypatched in tests)
    data_file.parent.mkdir(parents=True, exist_ok=True)

    # FIX [REVIEW 1.3]: Write to a sibling .tmp file first, then atomically
    # replace the live file.  os.replace() is atomic on both POSIX and Windows
    # NTFS, so the database is never left in a half-written state.
    tmp_file = data_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp_file, data_file)


# ---------------------------------------------------------------------------
# Generic helper
# ---------------------------------------------------------------------------

# FIX [REVIEW 2.1]: Changed return type from Optional[int] to int | None
# (idiomatic Python 3.10+ style; from __future__ import annotations is active).
def find_entry_index(entries: list[Any], key: str, value: Any) -> int | None:
    """Return the list index of the first entry where entry[key] == value, or None."""
    for i, entry in enumerate(entries):
        if entry[key] == value:
            return i
    return None


# ---------------------------------------------------------------------------
# VLAN CRUD
# ---------------------------------------------------------------------------

def add_vlan(data: NetworkData, vlan: Vlan) -> None:
    """Append a VLAN entry; raises ValueError if the VLAN ID already exists."""
    if any(v["id"] == vlan["id"] for v in data["vlans"]):
        raise ValueError(f"VLAN {vlan['id']} already exists.")
    data["vlans"].append(vlan)


def update_vlan(data: NetworkData, index: int, updates: dict[str, Any]) -> None:
    """Apply field updates to the VLAN at the given data-list index."""
    data["vlans"][index].update(updates)


def delete_vlan(data: NetworkData, index: int) -> None:
    """Remove the VLAN at the given data-list index."""
    data["vlans"].pop(index)


def list_vlans(data: NetworkData) -> list[Vlan]:
    """Return all VLANs sorted ascending by VLAN ID."""
    return sorted(data["vlans"], key=lambda v: v["id"])


# ---------------------------------------------------------------------------
# Server CRUD
# ---------------------------------------------------------------------------

def add_server(data: NetworkData, server: Server) -> None:
    """Append a server entry; raises ValueError if the hostname already exists."""
    if any(s["hostname"] == server["hostname"] for s in data["servers"]):
        raise ValueError(f"Server '{server['hostname']}' already exists.")
    data["servers"].append(server)


def update_server(data: NetworkData, index: int, updates: dict[str, Any]) -> None:
    """Apply field updates to the server at the given data-list index."""
    data["servers"][index].update(updates)


def delete_server(data: NetworkData, index: int) -> None:
    """Remove the server at the given data-list index."""
    data["servers"].pop(index)


def list_servers(data: NetworkData) -> list[Server]:
    """Return all servers sorted alphabetically by hostname."""
    return sorted(data["servers"], key=lambda s: s["hostname"])


# ---------------------------------------------------------------------------
# Switch CRUD
# ---------------------------------------------------------------------------

def add_switch(data: NetworkData, switch: Switch) -> None:
    """Append a switch entry; raises ValueError if the name already exists."""
    if any(s["name"] == switch["name"] for s in data["switches"]):
        raise ValueError(f"Switch '{switch['name']}' already exists.")
    data["switches"].append(switch)


def update_switch(data: NetworkData, index: int, updates: dict[str, Any]) -> None:
    """Apply field updates to the switch at the given data-list index."""
    data["switches"][index].update(updates)


def delete_switch(data: NetworkData, index: int) -> None:
    """Remove the switch at the given data-list index."""
    data["switches"].pop(index)


def list_switches(data: NetworkData) -> list[Switch]:
    """Return all switches sorted alphabetically by name."""
    return sorted(data["switches"], key=lambda s: s["name"])


# ---------------------------------------------------------------------------
# DHCP Scope CRUD
# ---------------------------------------------------------------------------

def add_dhcp_scope(data: NetworkData, scope: DhcpScope) -> None:
    """Append a DHCP scope entry; raises ValueError if the name already exists."""
    if any(s["name"] == scope["name"] for s in data["dhcp_scopes"]):
        raise ValueError(f"DHCP scope '{scope['name']}' already exists.")
    data["dhcp_scopes"].append(scope)


def update_dhcp_scope(data: NetworkData, index: int, updates: dict[str, Any]) -> None:
    """Apply field updates to the DHCP scope at the given data-list index."""
    data["dhcp_scopes"][index].update(updates)


def delete_dhcp_scope(data: NetworkData, index: int) -> None:
    """Remove the DHCP scope at the given data-list index."""
    data["dhcp_scopes"].pop(index)


def list_dhcp_scopes(data: NetworkData) -> list[DhcpScope]:
    """Return all DHCP scopes sorted alphabetically by name."""
    return sorted(data["dhcp_scopes"], key=lambda s: s["name"])
