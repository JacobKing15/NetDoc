"""
export.py - Network documentation export module.

Provides functions to export network data (VLANs, servers, switches, DHCP scopes)
to Markdown and HTML formats.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

# FIX [REVIEW 2.2]: Import the canonical NetworkData TypedDict from data.py instead
# of redefining a looser dict[str, list[dict[str, Any]]] alias here.  The two
# definitions were incompatible at the type-checker level.
from modules.data import NetworkData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current timestamp as a human-readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write_file(path: str, content: str) -> str:
    """Write *content* to *path*, creating parent directories if needed.

    Returns the resolved output path on success.
    Raises ``OSError`` if the file cannot be written.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        raise OSError(f"Failed to write export file '{path}': {exc}") from exc
    return path


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a GitHub-Flavoured Markdown table string.

    Parameters
    ----------
    headers:
        Column header labels.
    rows:
        Each inner list is one data row; values are coerced to ``str``.
    """
    header_row = "| " + " | ".join(headers) + " |"
    separator  = "| " + " | ".join("---" for _ in headers) + " |"
    # FIX [REVIEW 3.2]: Escape pipe characters inside cell values so that a field
    # containing '|' (e.g. "Primary | Backup") does not break the Markdown table
    # structure in any GFM-compliant renderer.
    data_rows  = [
        "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, separator] + data_rows)


# FIX [REVIEW 2.3]: Added -> str return type annotations to all private
# table-builder functions (they were the only unannotated functions in this module).
def _vlans_md(vlans: list[dict[str, Any]]) -> str:
    headers = ["ID", "Name", "Subnet", "Purpose"]
    if not vlans:
        rows = [["No entries yet.", "", "", ""]]
    else:
        rows = [[v.get("id", ""), v.get("name", ""), v.get("subnet", ""), v.get("purpose", "")] for v in vlans]
    return _md_table(headers, rows)


def _servers_md(servers: list[dict[str, Any]]) -> str:
    headers = ["Hostname", "IP", "Role", "Location"]
    if not servers:
        rows = [["No entries yet.", "", "", ""]]
    else:
        rows = [[s.get("hostname", ""), s.get("ip", ""), s.get("role", ""), s.get("location", "")] for s in servers]
    return _md_table(headers, rows)


def _switches_md(switches: list[dict[str, Any]]) -> str:
    headers = ["Name", "IP", "Location", "Uplink"]
    if not switches:
        rows = [["No entries yet.", "", "", ""]]
    else:
        rows = [[s.get("name", ""), s.get("ip", ""), s.get("location", ""), s.get("uplink", "")] for s in switches]
    return _md_table(headers, rows)


def _dhcp_md(scopes: list[dict[str, Any]]) -> str:
    headers = ["Name", "Range", "Gateway", "DNS"]
    if not scopes:
        rows = [["No entries yet.", "", "", ""]]
    else:
        rows = [[s.get("name", ""), s.get("range", ""), s.get("gateway", ""), s.get("dns", "")] for s in scopes]
    return _md_table(headers, rows)


def export_markdown(data: NetworkData, output_path: str) -> str:
    """Export network documentation to a Markdown file.

    Generates a structured Markdown document containing tables for VLANs,
    servers, switches, and DHCP scopes.  Sections with no data show a
    placeholder row instead of an empty table.

    Parameters
    ----------
    data:
        Network data dictionary with keys ``vlans``, ``servers``,
        ``switches``, and ``dhcp_scopes``.  Missing keys are treated as
        empty lists.
    output_path:
        Destination file path (e.g. ``"output/network_docs.md"``).

    Returns
    -------
    str
        The resolved path of the written file.

    Raises
    ------
    OSError
        If the file cannot be created or written.
    """
    vlans       = data.get("vlans", [])
    servers     = data.get("servers", [])
    switches    = data.get("switches", [])
    dhcp_scopes = data.get("dhcp_scopes", [])
    timestamp   = _now()

    lines: list[str] = [
        "# Network Documentation",
        "",
        f"_Generated: {timestamp}_",
        "",
        "---",
        "",
        "## VLANs",
        "",
        _vlans_md(vlans),
        "",
        "---",
        "",
        "## Servers",
        "",
        _servers_md(servers),
        "",
        "---",
        "",
        "## Switches",
        "",
        _switches_md(switches),
        "",
        "---",
        "",
        "## DHCP Scopes",
        "",
        _dhcp_md(dhcp_scopes),
        "",
    ]

    content = "\n".join(lines)
    return _write_file(output_path, content)


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------

_HTML_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        background: #ffffff;
        color: #1a1a2e;
    }

    header {
        background: #0d1b2a;
        color: #ffffff;
        padding: 28px 40px;
    }

    header h1 {
        font-size: 1.8rem;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    header p {
        margin-top: 6px;
        font-size: 0.85rem;
        color: #a0aec0;
    }

    main {
        max-width: 1100px;
        margin: 40px auto;
        padding: 0 24px 60px;
    }

    h2 {
        font-size: 1.2rem;
        font-weight: 600;
        color: #0d1b2a;
        margin: 40px 0 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #e2e8f0;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }

    thead tr {
        background: #0d1b2a;
        color: #ffffff;
    }

    thead th {
        text-align: left;
        padding: 10px 14px;
        font-weight: 500;
        letter-spacing: 0.03em;
    }

    tbody tr:nth-child(odd)  { background: #f7f9fc; }
    tbody tr:nth-child(even) { background: #edf2f7; }

    tbody tr:hover { background: #dbeafe; }

    tbody td {
        padding: 9px 14px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
    }

    .placeholder {
        color: #a0aec0;
        font-style: italic;
    }

    footer {
        background: #0d1b2a;
        color: #a0aec0;
        text-align: center;
        padding: 16px;
        font-size: 0.8rem;
    }
"""


def _html_escape(text: str) -> str:
    """Minimally escape characters that are unsafe inside HTML text nodes."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html_table(headers: list[str], rows: list[list[str]], *, placeholder: bool = False) -> str:
    """Render an HTML ``<table>`` element.

    Parameters
    ----------
    headers:
        Column header labels.
    rows:
        Data rows; each inner list maps positionally to *headers*.
    placeholder:
        When ``True``, the first cell of the single row receives the
        ``placeholder`` CSS class.
    """
    th_cells = "".join(f"<th>{_html_escape(h)}</th>" for h in headers)
    thead = f"<thead><tr>{th_cells}</tr></thead>"

    body_rows: list[str] = []
    for row in rows:
        cells: list[str] = []
        for idx, cell in enumerate(row):
            cls = ' class="placeholder"' if (placeholder and idx == 0) else ""
            cells.append(f"<td{cls}>{_html_escape(str(cell))}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    tbody = "<tbody>" + "".join(body_rows) + "</tbody>"
    return f'<table>{thead}{tbody}</table>'


# FIX [REVIEW 2.3]: Added -> str return type annotations (continued).
def _vlans_html(vlans: list[dict[str, Any]]) -> str:
    headers = ["ID", "Name", "Subnet", "Purpose"]
    if not vlans:
        return _html_table(headers, [["No entries yet.", "", "", ""]], placeholder=True)
    rows = [[v.get("id", ""), v.get("name", ""), v.get("subnet", ""), v.get("purpose", "")] for v in vlans]
    return _html_table(headers, rows)


def _servers_html(servers: list[dict[str, Any]]) -> str:
    headers = ["Hostname", "IP", "Role", "Location"]
    if not servers:
        return _html_table(headers, [["No entries yet.", "", "", ""]], placeholder=True)
    rows = [[s.get("hostname", ""), s.get("ip", ""), s.get("role", ""), s.get("location", "")] for s in servers]
    return _html_table(headers, rows)


def _switches_html(switches: list[dict[str, Any]]) -> str:
    headers = ["Name", "IP", "Location", "Uplink"]
    if not switches:
        return _html_table(headers, [["No entries yet.", "", "", ""]], placeholder=True)
    rows = [[s.get("name", ""), s.get("ip", ""), s.get("location", ""), s.get("uplink", "")] for s in switches]
    return _html_table(headers, rows)


def _dhcp_html(scopes: list[dict[str, Any]]) -> str:
    headers = ["Name", "Range", "Gateway", "DNS"]
    if not scopes:
        return _html_table(headers, [["No entries yet.", "", "", ""]], placeholder=True)
    rows = [[s.get("name", ""), s.get("range", ""), s.get("gateway", ""), s.get("dns", "")] for s in scopes]
    return _html_table(headers, rows)


def export_html(data: NetworkData, output_path: str) -> str:
    """Export network documentation to a self-contained HTML file.

    Produces a fully inline-styled HTML page (no external dependencies) with:

    - A dark navy header displaying the document title and generation time.
    - One table per section (VLANs, Servers, Switches, DHCP Scopes) with
      alternating row colours and hover highlighting.
    - A footer repeating the generation timestamp.
    - Placeholder rows for any empty section.

    Parameters
    ----------
    data:
        Network data dictionary with keys ``vlans``, ``servers``,
        ``switches``, and ``dhcp_scopes``.  Missing keys are treated as
        empty lists.
    output_path:
        Destination file path (e.g. ``"output/network_docs.html"``).

    Returns
    -------
    str
        The resolved path of the written file.

    Raises
    ------
    OSError
        If the file cannot be created or written.
    """
    vlans       = data.get("vlans", [])
    servers     = data.get("servers", [])
    switches    = data.get("switches", [])
    dhcp_scopes = data.get("dhcp_scopes", [])
    timestamp   = _now()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Network Documentation</title>
  <style>{_HTML_CSS}
  </style>
</head>
<body>

<header>
  <h1>Network Documentation</h1>
  <p>Generated: {_html_escape(timestamp)}</p>
</header>

<main>

  <h2>VLANs</h2>
  {_vlans_html(vlans)}

  <h2>Servers</h2>
  {_servers_html(servers)}

  <h2>Switches</h2>
  {_switches_html(switches)}

  <h2>DHCP Scopes</h2>
  {_dhcp_html(dhcp_scopes)}

</main>

<footer>
  <p>Network Documentation &mdash; Generated: {_html_escape(timestamp)}</p>
</footer>

</body>
</html>
"""

    return _write_file(output_path, html)
