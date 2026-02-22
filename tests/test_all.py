"""
Comprehensive unit tests for the Network Documentation Generator.

Covers:
  - CRUD operations for all four data types (vlans, servers, switches, dhcp_scopes)
  - Duplicate-entry rejection enforced by each add_* function
  - Credential detection logic in cli.looks_like_credential
  - Markdown and HTML export with both populated and empty data
  - Malformed / missing JSON file handling in data.load_data

Run from the project root with:
    pytest tests/test_all.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Make sure the project root is importable so that `from modules.X import ...`
# works whether pytest is invoked from the project root or the tests/ folder.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.data as data_module
from modules.data import (
    _empty_data,
    load_data,
    save_data,
    find_entry_index,
    add_vlan,    update_vlan,   delete_vlan,   list_vlans,
    add_server,  update_server, delete_server, list_servers,
    add_switch,  update_switch, delete_switch, list_switches,
    add_dhcp_scope, update_dhcp_scope, delete_dhcp_scope, list_dhcp_scopes,
)
from modules.cli import looks_like_credential
from modules.export import export_markdown, export_html


# ===========================================================================
# Shared fixtures
# ===========================================================================

@pytest.fixture()
def patched_data_file(tmp_path, monkeypatch):
    """Redirect DATA_FILE to a temp directory so no real data files are touched."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    data_file = data_dir / "network.json"
    monkeypatch.setattr(data_module, "DATA_FILE", str(data_file))
    return data_file


@pytest.fixture()
def empty_data():
    """Return a freshly initialised empty NetworkData structure."""
    return _empty_data()


@pytest.fixture()
def populated_data():
    """Return a NetworkData structure pre-filled with one entry per category."""
    data = _empty_data()
    data["vlans"].append(
        {"id": 10, "name": "Management", "subnet": "10.0.10.0/24", "purpose": "Network management"}
    )
    data["servers"].append(
        {"hostname": "web-01", "ip": "10.0.10.5", "role": "web", "location": "Rack A1"}
    )
    data["switches"].append(
        {"name": "core-sw-01", "ip": "10.0.10.1", "location": "MDF", "uplink": "ge-0/0/0 to router"}
    )
    data["dhcp_scopes"].append(
        {"name": "LAN Scope", "range": "10.0.10.100-10.0.10.200", "gateway": "10.0.10.1", "dns": "8.8.8.8"}
    )
    return data


# ===========================================================================
# data.py — VLAN CRUD
# ===========================================================================

class TestVlanCrud:

    # Verifies that a new VLAN is appended, saved, and survives a reload cycle.
    def test_add_vlan_persists(self, patched_data_file):
        data = _empty_data()
        add_vlan(data, {"id": 10, "name": "Management", "subnet": "10.0.10.0/24", "purpose": "Mgmt traffic"})
        save_data(data)

        reloaded = load_data()
        assert len(reloaded["vlans"]) == 1
        assert reloaded["vlans"][0]["id"] == 10
        assert reloaded["vlans"][0]["name"] == "Management"
        assert reloaded["vlans"][0]["subnet"] == "10.0.10.0/24"

    # Verifies that adding a second VLAN with the same ID raises ValueError.
    def test_add_vlan_duplicate_id_raises(self):
        data = _empty_data()
        add_vlan(data, {"id": 10, "name": "Mgmt", "subnet": "10.0.10.0/24", "purpose": "test"})
        with pytest.raises(ValueError, match="10"):
            add_vlan(data, {"id": 10, "name": "Other", "subnet": "10.0.11.0/24", "purpose": "test"})

    # Verifies that update_vlan applies field changes in-place on the data dict.
    def test_edit_vlan(self):
        data = _empty_data()
        add_vlan(data, {"id": 20, "name": "Guest", "subnet": "10.0.20.0/24", "purpose": "Guests"})
        idx = find_entry_index(data["vlans"], "id", 20)
        update_vlan(data, idx, {"name": "Guest-WiFi", "purpose": "Wireless guests"})
        assert data["vlans"][idx]["name"] == "Guest-WiFi"
        assert data["vlans"][idx]["purpose"] == "Wireless guests"

    # Verifies that delete_vlan removes the entry and leaves the list empty.
    def test_delete_vlan(self):
        data = _empty_data()
        add_vlan(data, {"id": 30, "name": "IoT", "subnet": "10.0.30.0/24", "purpose": "IoT devices"})
        idx = find_entry_index(data["vlans"], "id", 30)
        delete_vlan(data, idx)
        assert len(data["vlans"]) == 0

    # Verifies that list_vlans returns entries sorted by VLAN ID ascending.
    def test_list_vlans_sorted_by_id(self):
        data = _empty_data()
        add_vlan(data, {"id": 100, "name": "Voice", "subnet": "10.0.100.0/24", "purpose": "VoIP"})
        add_vlan(data, {"id": 10,  "name": "Mgmt",  "subnet": "10.0.10.0/24",  "purpose": "Mgmt"})
        result = list_vlans(data)
        assert result[0]["id"] == 10
        assert result[1]["id"] == 100


# ===========================================================================
# data.py — Server CRUD
# ===========================================================================

class TestServerCrud:

    # Verifies that a new server is appended, saved, and survives a reload cycle.
    def test_add_server_persists(self, patched_data_file):
        data = _empty_data()
        add_server(data, {"hostname": "db-01", "ip": "10.0.10.10", "role": "database", "location": "Rack B2"})
        save_data(data)

        reloaded = load_data()
        assert len(reloaded["servers"]) == 1
        assert reloaded["servers"][0]["hostname"] == "db-01"
        assert reloaded["servers"][0]["ip"] == "10.0.10.10"

    # Verifies that adding a second server with the same hostname raises ValueError.
    def test_add_server_duplicate_hostname_raises(self):
        data = _empty_data()
        add_server(data, {"hostname": "web-01", "ip": "10.0.1.1", "role": "web", "location": "Rack A1"})
        with pytest.raises(ValueError, match="web-01"):
            add_server(data, {"hostname": "web-01", "ip": "10.0.1.2", "role": "web", "location": "Rack A2"})

    # Verifies that update_server applies field changes in-place on the data dict.
    def test_edit_server(self):
        data = _empty_data()
        add_server(data, {"hostname": "app-01", "ip": "10.0.1.5", "role": "app", "location": "Rack C1"})
        idx = find_entry_index(data["servers"], "hostname", "app-01")
        update_server(data, idx, {"role": "api-gateway", "location": "Rack C2"})
        assert data["servers"][idx]["role"] == "api-gateway"
        assert data["servers"][idx]["location"] == "Rack C2"

    # Verifies that delete_server removes the entry and leaves the list empty.
    def test_delete_server(self):
        data = _empty_data()
        add_server(data, {"hostname": "backup-01", "ip": "10.0.1.20", "role": "backup", "location": "Rack D1"})
        idx = find_entry_index(data["servers"], "hostname", "backup-01")
        delete_server(data, idx)
        assert len(data["servers"]) == 0

    # Verifies that list_servers returns entries sorted alphabetically by hostname.
    def test_list_servers_sorted_by_hostname(self):
        data = _empty_data()
        add_server(data, {"hostname": "web-01",    "ip": "10.0.1.1", "role": "web",    "location": "A1"})
        add_server(data, {"hostname": "backup-01", "ip": "10.0.1.2", "role": "backup", "location": "B1"})
        result = list_servers(data)
        assert result[0]["hostname"] == "backup-01"
        assert result[1]["hostname"] == "web-01"


# ===========================================================================
# data.py — Switch CRUD
# ===========================================================================

class TestSwitchCrud:

    # Verifies that a new switch is appended, saved, and survives a reload cycle.
    def test_add_switch_persists(self, patched_data_file):
        data = _empty_data()
        add_switch(data, {"name": "core-sw-01", "ip": "10.0.10.1", "location": "MDF", "uplink": "ge-0/0/0 to router"})
        save_data(data)

        reloaded = load_data()
        assert len(reloaded["switches"]) == 1
        assert reloaded["switches"][0]["name"] == "core-sw-01"
        assert reloaded["switches"][0]["location"] == "MDF"

    # Verifies that adding a second switch with the same name raises ValueError.
    def test_add_switch_duplicate_name_raises(self):
        data = _empty_data()
        add_switch(data, {"name": "access-sw-01", "ip": "10.0.10.2", "location": "IDF-1", "uplink": "core"})
        with pytest.raises(ValueError, match="access-sw-01"):
            add_switch(data, {"name": "access-sw-01", "ip": "10.0.10.3", "location": "IDF-2", "uplink": "core"})

    # Verifies that update_switch applies field changes in-place on the data dict.
    def test_edit_switch(self):
        data = _empty_data()
        add_switch(data, {"name": "edge-sw-01", "ip": "10.0.10.5", "location": "IDF-2", "uplink": "core-sw-01"})
        idx = find_entry_index(data["switches"], "name", "edge-sw-01")
        update_switch(data, idx, {"ip": "10.0.10.6", "location": "IDF-3"})
        assert data["switches"][idx]["ip"] == "10.0.10.6"
        assert data["switches"][idx]["location"] == "IDF-3"

    # Verifies that delete_switch removes the entry and leaves the list empty.
    def test_delete_switch(self):
        data = _empty_data()
        add_switch(data, {"name": "old-sw-01", "ip": "10.0.10.9", "location": "IDF-1", "uplink": "core"})
        idx = find_entry_index(data["switches"], "name", "old-sw-01")
        delete_switch(data, idx)
        assert len(data["switches"]) == 0

    # Verifies that list_switches returns entries sorted alphabetically by name.
    def test_list_switches_sorted_by_name(self):
        data = _empty_data()
        add_switch(data, {"name": "z-sw-01", "ip": "10.0.1.1", "location": "IDF-1", "uplink": "core"})
        add_switch(data, {"name": "a-sw-01", "ip": "10.0.1.2", "location": "IDF-2", "uplink": "core"})
        result = list_switches(data)
        assert result[0]["name"] == "a-sw-01"
        assert result[1]["name"] == "z-sw-01"


# ===========================================================================
# data.py — DHCP Scope CRUD
# ===========================================================================

class TestDhcpScopeCrud:

    # Verifies that a new DHCP scope is appended, saved, and survives a reload.
    def test_add_dhcp_scope_persists(self, patched_data_file):
        data = _empty_data()
        add_dhcp_scope(data, {"name": "LAN", "range": "10.0.10.100-10.0.10.200", "gateway": "10.0.10.1", "dns": "8.8.8.8"})
        save_data(data)

        reloaded = load_data()
        assert len(reloaded["dhcp_scopes"]) == 1
        assert reloaded["dhcp_scopes"][0]["name"] == "LAN"
        assert reloaded["dhcp_scopes"][0]["gateway"] == "10.0.10.1"

    # Verifies that adding a second scope with the same name raises ValueError.
    def test_add_dhcp_scope_duplicate_name_raises(self):
        data = _empty_data()
        add_dhcp_scope(data, {"name": "Guest", "range": "10.0.20.100-200", "gateway": "10.0.20.1", "dns": "8.8.8.8"})
        with pytest.raises(ValueError, match="Guest"):
            add_dhcp_scope(data, {"name": "Guest", "range": "10.0.20.50-100", "gateway": "10.0.20.1", "dns": "1.1.1.1"})

    # Verifies that update_dhcp_scope applies field changes in-place on the data dict.
    def test_edit_dhcp_scope(self):
        data = _empty_data()
        add_dhcp_scope(data, {"name": "Servers", "range": "10.0.10.50-100", "gateway": "10.0.10.1", "dns": "8.8.8.8"})
        idx = find_entry_index(data["dhcp_scopes"], "name", "Servers")
        update_dhcp_scope(data, idx, {"range": "10.0.10.50-150", "dns": "1.1.1.1"})
        assert data["dhcp_scopes"][idx]["range"] == "10.0.10.50-150"
        assert data["dhcp_scopes"][idx]["dns"] == "1.1.1.1"

    # Verifies that delete_dhcp_scope removes the entry and leaves the list empty.
    def test_delete_dhcp_scope(self):
        data = _empty_data()
        add_dhcp_scope(data, {"name": "Old-Scope", "range": "192.168.1.100-200", "gateway": "192.168.1.1", "dns": "8.8.8.8"})
        idx = find_entry_index(data["dhcp_scopes"], "name", "Old-Scope")
        delete_dhcp_scope(data, idx)
        assert len(data["dhcp_scopes"]) == 0

    # Verifies that list_dhcp_scopes returns entries sorted alphabetically by name.
    def test_list_dhcp_scopes_sorted_by_name(self):
        data = _empty_data()
        add_dhcp_scope(data, {"name": "WLAN", "range": "10.0.30.100-200", "gateway": "10.0.30.1", "dns": "8.8.8.8"})
        add_dhcp_scope(data, {"name": "LAN",  "range": "10.0.10.100-200", "gateway": "10.0.10.1", "dns": "8.8.8.8"})
        result = list_dhcp_scopes(data)
        assert result[0]["name"] == "LAN"
        assert result[1]["name"] == "WLAN"


# ===========================================================================
# cli.py — credential detection (looks_like_credential)
# ===========================================================================

class TestCredentialDetection:

    # Verifies that the keyword "password" (standalone) is flagged as a credential.
    def test_detects_keyword_password(self):
        assert looks_like_credential("password") is True

    # Verifies that "secret" appearing as a whole word is flagged.
    def test_detects_keyword_secret(self):
        assert looks_like_credential("secret") is True

    # Verifies that "api_key" (with underscore separator) is flagged.
    def test_detects_keyword_api_key(self):
        assert looks_like_credential("api_key") is True

    # Verifies that "auth_token" is flagged as a credential keyword.
    def test_detects_keyword_auth_token(self):
        assert looks_like_credential("auth_token") is True

    # Verifies that "private_key" is flagged as a credential keyword.
    def test_detects_keyword_private_key(self):
        assert looks_like_credential("private_key") is True

    # Verifies that "credential" by itself is flagged.
    def test_detects_keyword_credential(self):
        assert looks_like_credential("credential") is True

    # Verifies that "passwd" (abbreviated form) is flagged.
    def test_detects_keyword_passwd(self):
        assert looks_like_credential("passwd") is True

    # Verifies that keyword matching is case-insensitive ("PASSWORD" is still caught).
    def test_detects_keyword_case_insensitive(self):
        assert looks_like_credential("PASSWORD") is True

    # Verifies that a strong generated password (8+ chars with all four character
    # classes: uppercase, lowercase, digit, special symbol) triggers the heuristic.
    def test_detects_strong_password_heuristic(self):
        assert looks_like_credential("Admin@1234") is True   # upper+lower+digit+special

    # Verifies that another strong-password pattern is caught by the heuristic.
    def test_detects_strong_password_heuristic_variant(self):
        assert looks_like_credential("P@ssw0rd!") is True

    # Verifies that a typical VLAN name is NOT flagged as a credential.
    def test_accepts_vlan_name(self):
        assert looks_like_credential("Management-VLAN") is False

    # Verifies that a plain IPv4 address is not flagged.
    def test_accepts_ip_address(self):
        assert looks_like_credential("192.168.1.1") is False

    # Verifies that a CIDR subnet string is not flagged.
    def test_accepts_subnet(self):
        assert looks_like_credential("10.0.10.0/24") is False

    # Verifies that a short mixed-character string below the 8-char length
    # threshold does not trigger the heuristic even with all character classes.
    def test_accepts_short_mixed_string(self):
        assert looks_like_credential("Ab1!") is False      # only 4 chars

    # Verifies that a long string missing one character class (no special char)
    # is not flagged, since all four classes are required.
    def test_accepts_long_string_missing_special(self):
        assert looks_like_credential("AdminUser1234") is False  # no special char

    # Verifies that a hostname-style string is not flagged.
    def test_accepts_hostname(self):
        assert looks_like_credential("core-sw-01") is False

    # Verifies that a DHCP range string is not flagged.
    def test_accepts_dhcp_range(self):
        assert looks_like_credential("10.0.10.100-10.0.10.200") is False


# ===========================================================================
# export.py — Markdown export
# ===========================================================================

class TestExportMarkdown:

    # Verifies that exporting populated data writes a file containing all four
    # section headers and the actual data values from each category.
    def test_markdown_with_data(self, tmp_path, populated_data):
        out_file = tmp_path / "docs.md"
        result_path = export_markdown(populated_data, str(out_file))

        assert Path(result_path).exists()
        content = out_file.read_text(encoding="utf-8")

        # Document structure
        assert "# Network Documentation" in content
        assert "## VLANs" in content
        assert "## Servers" in content
        assert "## Switches" in content
        assert "## DHCP Scopes" in content

        # VLAN row values
        assert "Management" in content
        assert "10.0.10.0/24" in content

        # Server row values
        assert "web-01" in content
        assert "10.0.10.5" in content

        # Switch row values
        assert "core-sw-01" in content

        # DHCP scope row values
        assert "LAN Scope" in content
        assert "10.0.10.100-10.0.10.200" in content

    # Verifies that exporting empty data still produces a valid Markdown file
    # with a "No entries yet." placeholder row in each of the four sections.
    def test_markdown_with_empty_data(self, tmp_path, empty_data):
        out_file = tmp_path / "empty.md"
        result_path = export_markdown(empty_data, str(out_file))

        assert Path(result_path).exists()
        content = out_file.read_text(encoding="utf-8")

        assert "# Network Documentation" in content
        # One placeholder per section (four sections total).
        assert content.count("No entries yet.") == 4

    # Verifies that the function returns the exact path it was given.
    def test_markdown_returns_output_path(self, tmp_path, empty_data):
        out_file = tmp_path / "network.md"
        result_path = export_markdown(empty_data, str(out_file))
        assert result_path == str(out_file)

    # Verifies that every table row uses the GFM pipe-delimited format
    # (starts and ends with "|").
    def test_markdown_table_pipe_format(self, tmp_path, populated_data):
        out_file = tmp_path / "table_test.md"
        export_markdown(populated_data, str(out_file))
        content = out_file.read_text(encoding="utf-8")

        pipe_lines = [ln for ln in content.splitlines() if ln.startswith("|")]
        assert len(pipe_lines) > 0
        for line in pipe_lines:
            assert line.endswith("|"), f"Table line does not end with '|': {line!r}"

    # Verifies that the generated timestamp line is present in the output.
    def test_markdown_contains_timestamp(self, tmp_path, empty_data):
        out_file = tmp_path / "ts_test.md"
        export_markdown(empty_data, str(out_file))
        content = out_file.read_text(encoding="utf-8")
        assert "_Generated:" in content


# ===========================================================================
# export.py — HTML export
# ===========================================================================

class TestExportHtml:

    # Verifies that exporting populated data produces a valid HTML document
    # with all section headings and actual data values present.
    def test_html_with_data(self, tmp_path, populated_data):
        out_file = tmp_path / "docs.html"
        result_path = export_html(populated_data, str(out_file))

        assert Path(result_path).exists()
        content = out_file.read_text(encoding="utf-8")

        # Document shell
        assert "<!DOCTYPE html>" in content
        assert "<title>Network Documentation</title>" in content

        # Section headings
        assert "<h2>VLANs</h2>" in content
        assert "<h2>Servers</h2>" in content
        assert "<h2>Switches</h2>" in content
        assert "<h2>DHCP Scopes</h2>" in content

        # VLAN data
        assert "Management" in content
        assert "10.0.10.0/24" in content

        # Server data
        assert "web-01" in content
        assert "10.0.10.5" in content

        # Switch data
        assert "core-sw-01" in content

        # DHCP scope data
        assert "LAN Scope" in content
        assert "10.0.10.100-10.0.10.200" in content

    # Verifies that exporting empty data produces a valid HTML file with
    # placeholder cells styled with the 'placeholder' CSS class in each section.
    def test_html_with_empty_data(self, tmp_path, empty_data):
        out_file = tmp_path / "empty.html"
        result_path = export_html(empty_data, str(out_file))

        assert Path(result_path).exists()
        content = out_file.read_text(encoding="utf-8")

        assert "<!DOCTYPE html>" in content
        # Four sections → four placeholder rows, each with the placeholder class.
        assert content.count('class="placeholder"') == 4
        assert content.count("No entries yet.") == 4

    # Verifies that the function returns the exact path it was given.
    def test_html_returns_output_path(self, tmp_path, empty_data):
        out_file = tmp_path / "network.html"
        result_path = export_html(empty_data, str(out_file))
        assert result_path == str(out_file)

    # Verifies that HTML special characters in data values are escaped so they
    # render as text rather than being interpreted as markup (XSS prevention).
    def test_html_escapes_special_characters(self, tmp_path):
        data = _empty_data()
        data["vlans"].append({
            "id": 1,
            "name": "<script>alert('xss')</script>",
            "subnet": "10.0.0.0/8",
            "purpose": "Test & verify",
        })
        out_file = tmp_path / "escape_test.html"
        export_html(data, str(out_file))
        content = out_file.read_text(encoding="utf-8")

        # Raw tag must not appear; its escaped form must be present.
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

        # Ampersand must be escaped.
        assert "&amp;" in content

    # Verifies that the HTML document contains a <footer> element with a
    # timestamp, matching the structure defined in export.py.
    def test_html_contains_footer(self, tmp_path, empty_data):
        out_file = tmp_path / "footer_test.html"
        export_html(empty_data, str(out_file))
        content = out_file.read_text(encoding="utf-8")
        assert "<footer>" in content
        assert "Generated:" in content


# ===========================================================================
# data.py — malformed / missing JSON handling
# ===========================================================================

class TestMalformedJson:

    # Verifies that loading a file containing syntactically invalid JSON raises
    # json.JSONDecodeError rather than silently returning empty or partial data.
    def test_malformed_json_raises_decode_error(self, patched_data_file):
        patched_data_file.write_text("{not valid json: [}", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_data()

    # Verifies that a completely empty file (0 bytes) also raises
    # json.JSONDecodeError because the empty string is not valid JSON.
    def test_empty_file_raises_decode_error(self, patched_data_file):
        patched_data_file.write_text("", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_data()

    # FIX [REVIEW 1.4]: load_data now validates the root structure at load time.
    # A JSON file whose root is a list raises ValueError immediately rather than
    # returning the raw list and causing a confusing AttributeError downstream.
    def test_wrong_root_type_is_not_a_dict(self, patched_data_file):
        patched_data_file.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid structure"):
            load_data()

    # Verifies that when the data file is absent entirely, load_data returns
    # a valid empty NetworkData structure without raising any exception.
    def test_missing_file_returns_empty_structure(self, patched_data_file):
        # patched_data_file points to a path that doesn't exist yet.
        result = load_data()
        assert result == {"vlans": [], "servers": [], "switches": [], "dhcp_scopes": []}

    # FIX [REVIEW 1.4]: JSON null is not a dict; load_data now raises ValueError
    # immediately rather than returning None and causing an AttributeError later.
    def test_null_json_is_not_a_dict(self, patched_data_file):
        patched_data_file.write_text("null", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid structure"):
            load_data()
