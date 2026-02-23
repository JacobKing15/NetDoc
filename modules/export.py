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


# ---------------------------------------------------------------------------
# RTF export (built-in only — no third-party libraries)
# ---------------------------------------------------------------------------

def _rtf_escape(text: str) -> str:
    """Escape special RTF characters; encode non-ASCII as RTF Unicode escapes.

    RTF control words use backslash, braces are structural, and code points
    above 127 are represented as ``\\uN?`` (signed 16-bit decimal) so the
    output is always pure ASCII.
    """
    result: list[str] = []
    for ch in str(text):
        code = ord(ch)
        if ch == "\\":
            result.append("\\\\")
        elif ch == "{":
            result.append("\\{")
        elif ch == "}":
            result.append("\\}")
        elif ch == "\n":
            result.append("\\line ")
        elif code > 127:
            # RTF \uN uses signed 16-bit decimal
            signed = code if code <= 32767 else code - 65536
            result.append(f"\\u{signed}?")
        else:
            result.append(ch)
    return "".join(result)


# RTF color-table indices (1-based)
_C_NAVY   = 1   # #0D1B2A  — header/table-header background
_C_WHITE  = 2   # #FFFFFF  — text on dark backgrounds
_C_ODD    = 3   # #F7F9FC  — odd data-row background
_C_EVEN   = 4   # #EDF2F7  — even data-row background
_C_BODY   = 5   # #1A1A2E  — body text on light backgrounds
_C_MUTED  = 6   # #A0AEC0  — muted text (subtitle, footer)
_C_BORDER = 7   # #E2E8F0  — light cell border colour

_RTF_COLOR_TABLE = (
    r"{\colortbl;"
    r"\red13\green27\blue42;"      # 1 navy
    r"\red255\green255\blue255;"   # 2 white
    r"\red247\green249\blue252;"   # 3 odd row
    r"\red237\green242\blue247;"   # 4 even row
    r"\red26\green26\blue46;"      # 5 body text
    r"\red160\green174\blue192;"   # 6 muted
    r"\red226\green232\blue240;"   # 7 border
    r"}"
)

# Cell borders using the light border colour
_CELL_BORDER = (
    f"\\clbrdrt\\brdrw8\\brdrs\\brdrcf{_C_BORDER}"
    f"\\clbrdrl\\brdrw8\\brdrs\\brdrcf{_C_BORDER}"
    f"\\clbrdrb\\brdrw8\\brdrs\\brdrcf{_C_BORDER}"
    f"\\clbrdrr\\brdrw8\\brdrs\\brdrcf{_C_BORDER}"
)

# Full-width column position (6-inch usable width at 1 440 twips/inch)
_PAGE_W = 8640


def _full_row(text: str, sub: str = "") -> str:
    """Dark navy full-width banner: large bold title + optional muted subtitle."""
    lines = [
        r"\trowd\trgaph0"
        r"\trpaddl144\trpaddfl3\trpaddr144\trpaddfr3"
        r"\trpaddt140\trpaddft3\trpaddb60\trpaddfb3",
        f"\\clcbpat{_C_NAVY}\\cellx{_PAGE_W}",
        f"\\pard\\intbl{{\\cf{_C_WHITE}\\b\\fs40 {_rtf_escape(text)}}}\\cell",
        r"\row",
    ]
    if sub:
        lines += [
            r"\trowd\trgaph0"
            r"\trpaddl144\trpaddfl3\trpaddr144\trpaddfr3"
            r"\trpaddt0\trpaddft3\trpaddb160\trpaddfb3",
            f"\\clcbpat{_C_NAVY}\\cellx{_PAGE_W}",
            f"\\pard\\intbl{{\\cf{_C_MUTED}\\fs18 {_rtf_escape(sub)}}}\\cell",
            r"\row",
        ]
    return "\n".join(lines)


def _footer_row(text: str) -> str:
    """Dark navy full-width footer row with centred muted text."""
    return "\n".join([
        r"\trowd\trgaph0"
        r"\trpaddl144\trpaddfl3\trpaddr144\trpaddfr3"
        r"\trpaddt100\trpaddft3\trpaddb100\trpaddfb3",
        f"\\clcbpat{_C_NAVY}\\cellx{_PAGE_W}",
        f"\\pard\\intbl\\qc{{\\cf{_C_MUTED}\\fs18 {_rtf_escape(text)}}}\\cell",
        r"\row",
    ])


def _rtf_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Return RTF markup for a styled table matching the HTML export design.

    - Header row: dark navy background, white bold text.
    - Data rows: alternating #F7F9FC / #EDF2F7 backgrounds.
    - All cells have a light (#E2E8F0) border.
    - Uses 8 640 twips (6 inches) of usable page width.
    """
    n = len(headers)
    col_w = _PAGE_W // n
    positions = [(i + 1) * col_w for i in range(n)]

    def _build_row(cells: list[str], bg: int, fg: int, bold: bool = False) -> str:
        parts = [
            r"\trowd\trgaph108"
            r"\trpaddl72\trpaddfl3\trpaddr72\trpaddfr3"
            r"\trpaddt72\trpaddft3\trpaddb72\trpaddfb3"
        ]
        for pos in positions:
            parts.append(f"\\clcbpat{bg}{_CELL_BORDER}\\cellx{pos}")
        for cell in cells:
            escaped = _rtf_escape(cell)
            fmt = f"\\b {escaped}\\b0" if bold else escaped
            parts.append(f"\\pard\\intbl{{\\cf{fg} {fmt}}}\\cell")
        parts.append(r"\row")
        return "\n".join(parts)

    lines = [_build_row(headers, bg=_C_NAVY, fg=_C_WHITE, bold=True)]
    if rows:
        for i, row in enumerate(rows):
            bg = _C_ODD if i % 2 == 0 else _C_EVEN
            lines.append(_build_row([str(c) for c in row], bg=bg, fg=_C_BODY))
    else:
        lines.append(_build_row(
            ["No entries yet."] + [""] * (n - 1), bg=_C_ODD, fg=_C_MUTED
        ))
    return "\n".join(lines)


def export_rtf(data: NetworkData, output_path: str) -> str:
    """Export network documentation to a professionally styled RTF file.

    Matches the visual design of the HTML export: dark navy header banner,
    navy table-header rows with white text, alternating row shading, and a
    dark navy footer — all using only Python built-ins.

    Parameters
    ----------
    data:
        Network data dictionary with keys ``vlans``, ``servers``,
        ``switches``, and ``dhcp_scopes``.
    output_path:
        Destination ``.rtf`` file path.

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

    def _heading(title: str) -> str:
        """Section heading: navy bold text with a navy underline rule."""
        return (
            f"\\pard\\sb360\\sa0"
            f"\\brdrb\\brdrw20\\brdrs\\brdrcf{_C_NAVY}"
            f"{{\\cf{_C_NAVY}\\b\\fs28 {_rtf_escape(title)}}}\\par\n"
            f"\\pard\\sb80\\sa0\\par\n"
        )

    vlans_rows    = [[str(v.get("id", "")), v.get("name", ""), v.get("subnet", ""), v.get("purpose", "")] for v in vlans]
    servers_rows  = [[s.get("hostname", ""), s.get("ip", ""), s.get("role", ""), s.get("location", "")] for s in servers]
    switches_rows = [[s.get("name", ""), s.get("ip", ""), s.get("location", ""), s.get("uplink", "")] for s in switches]
    dhcp_rows     = [[s.get("name", ""), s.get("range", ""), s.get("gateway", ""), s.get("dns", "")] for s in dhcp_scopes]

    parts = [
        r"{\rtf1\ansi\ansicpg1252\deff0\deflang1033",
        r"{\fonttbl{\f0\fswiss\fcharset0 Arial;}}",
        _RTF_COLOR_TABLE,
        r"\paperw12240\paperh15840\margl1800\margr1800\margt1440\margb1440\widowctrl",
        r"\f0\fs22",
        _full_row("Network Documentation", f"Generated: {timestamp}"),
        _heading("VLANs"),
        _rtf_table(["ID", "Name", "Subnet", "Purpose"], vlans_rows),
        r"\pard\sb80\sa0\par",
        _heading("Servers"),
        _rtf_table(["Hostname", "IP", "Role", "Location"], servers_rows),
        r"\pard\sb80\sa0\par",
        _heading("Switches"),
        _rtf_table(["Name", "IP", "Location", "Uplink"], switches_rows),
        r"\pard\sb80\sa0\par",
        _heading("DHCP Scopes"),
        _rtf_table(["Name", "Range", "Gateway", "DNS"], dhcp_rows),
        r"\pard\sb240\sa0\par",
        _footer_row(f"Network Documentation  |  Generated: {timestamp}"),
        "}",
    ]

    return _write_file(output_path, "\n".join(parts))
