"""Tkinter GUI for NetDoc - Network Documentation Generator.

Uses only Python's standard library (tkinter, pathlib, etc.).
No third-party dependencies are required.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Any

from modules import data as data_module
from modules.export import export_html, export_markdown


def _get_documents_dir() -> Path:
    """Return the real Windows Documents folder (handles OneDrive redirection).

    Uses the Windows Shell API (CSIDL_PERSONAL = 5) so it always returns the
    folder that File Explorer shows as Documents, even when OneDrive has
    redirected it.  Falls back to ~/Documents on non-Windows platforms.
    """
    if sys.platform == "win32":
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, 5, 0, 0, buf)
        if buf.value:
            return Path(buf.value)
    return Path.home() / "Documents"


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_PAD = 10
_BTN_W = 22          # main-window button width (characters)
_DIALOG_ENTRY_W = 32  # entry widget width in Add/Edit dialogs


# ---------------------------------------------------------------------------
# Section configuration
# ---------------------------------------------------------------------------

# Each entry: (label shown in dialog, dict key, type "int"|"str")
_FieldSpec = list[tuple[str, str, str]]

SECTION_CONFIG: dict[str, dict[str, Any]] = {
    "vlans": {
        "title":    "VLANs",
        "singular": "VLAN",
        "columns":  ("ID", "Name", "Subnet", "Purpose"),
        "fields":   [
            ("VLAN ID",  "id",      "int"),
            ("Name",     "name",    "str"),
            ("Subnet",   "subnet",  "str"),
            ("Purpose",  "purpose", "str"),
        ],
    },
    "servers": {
        "title":    "Servers",
        "singular": "Server",
        "columns":  ("Hostname", "IP", "Role", "Location"),
        "fields":   [
            ("Hostname",    "hostname", "str"),
            ("IP Address",  "ip",       "str"),
            ("Role",        "role",     "str"),
            ("Location",    "location", "str"),
        ],
    },
    "switches": {
        "title":    "Switches",
        "singular": "Switch",
        "columns":  ("Name", "IP", "Location", "Uplink"),
        "fields":   [
            ("Name",        "name",     "str"),
            ("IP Address",  "ip",       "str"),
            ("Location",    "location", "str"),
            ("Uplink",      "uplink",   "str"),
        ],
    },
    "dhcp_scopes": {
        "title":    "DHCP Scopes",
        "singular": "DHCP Scope",
        "columns":  ("Name", "Range", "Gateway", "DNS"),
        "fields":   [
            ("Name",    "name",    "str"),
            ("Range",   "range",   "str"),
            ("Gateway", "gateway", "str"),
            ("DNS",     "dns",     "str"),
        ],
    },
}

# Maps section key → CRUD functions from data_module
CRUD: dict[str, dict[str, Any]] = {
    "vlans": {
        "list":   data_module.list_vlans,
        "add":    data_module.add_vlan,
        "update": data_module.update_vlan,
        "delete": data_module.delete_vlan,
    },
    "servers": {
        "list":   data_module.list_servers,
        "add":    data_module.add_server,
        "update": data_module.update_server,
        "delete": data_module.delete_server,
    },
    "switches": {
        "list":   data_module.list_switches,
        "add":    data_module.add_switch,
        "update": data_module.update_switch,
        "delete": data_module.delete_switch,
    },
    "dhcp_scopes": {
        "list":   data_module.list_dhcp_scopes,
        "add":    data_module.add_dhcp_scope,
        "update": data_module.update_dhcp_scope,
        "delete": data_module.delete_dhcp_scope,
    },
}

# Field used as the unique identifier for find_entry_index
IDENTITY_FIELD: dict[str, str] = {
    "vlans":       "id",
    "servers":     "hostname",
    "switches":    "name",
    "dhcp_scopes": "name",
}


# ---------------------------------------------------------------------------
# Add / Edit dialog
# ---------------------------------------------------------------------------

class EntryDialog(tk.Toplevel):
    """Modal dialog for adding or editing a single record.

    Sets ``self.result`` to a populated dict on Save, or ``None`` on Cancel /
    Escape / window-close — so callers can check ``if dialog.result is None``
    to detect a cancelled operation with no side-effects.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        fields: _FieldSpec,
        initial_values: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)

        self.result: dict[str, Any] | None = None
        self._fields = fields
        self._vars: dict[str, tk.StringVar] = {}

        self._build(initial_values or {})

        # Escape and window-X both cancel without saving
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # Centre over parent and make modal
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, initial: dict[str, Any]) -> None:
        """Lay out the form fields and action buttons."""
        form = tk.Frame(self, padx=_PAD * 2, pady=_PAD)
        form.pack(fill="both", expand=True)

        self._first_entry: tk.Entry | None = None
        for row, (label, key, _type) in enumerate(self._fields):
            tk.Label(form, text=label + ":", anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, _PAD), pady=5
            )
            var = tk.StringVar(value=str(initial.get(key, "")))
            self._vars[key] = var
            entry = tk.Entry(form, textvariable=var, width=_DIALOG_ENTRY_W)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            if self._first_entry is None:
                self._first_entry = entry

        form.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self, padx=_PAD * 2, pady=_PAD)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Cancel", width=10,
                  command=self._cancel).pack(side="right", padx=(0, 0))
        tk.Button(btn_frame, text="Save", width=10,
                  command=self._save).pack(side="right", padx=(0, _PAD // 2))

        # Bind Enter key to Save
        self.bind("<Return>", lambda _e: self._save())

        if self._first_entry:
            self._first_entry.focus_set()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Validate inputs, populate ``self.result``, and close."""
        result: dict[str, Any] = {}
        for label, key, type_str in self._fields:
            raw = self._vars[key].get().strip()
            if not raw:
                messagebox.showerror(
                    "Validation Error",
                    f"'{label}' cannot be empty.",
                    parent=self,
                )
                return
            if type_str == "int":
                try:
                    result[key] = int(raw)
                except ValueError:
                    messagebox.showerror(
                        "Validation Error",
                        f"'{label}' must be a whole number.",
                        parent=self,
                    )
                    return
            else:
                result[key] = raw
        self.result = result
        self.destroy()

    def _cancel(self) -> None:
        """Close without saving — result stays None."""
        self.destroy()


# ---------------------------------------------------------------------------
# Section window (treeview list + CRUD buttons)
# ---------------------------------------------------------------------------

class SectionWindow(tk.Toplevel):
    """Manages listing, adding, editing, and deleting records for one section."""

    def __init__(self, parent: tk.Widget, section_key: str) -> None:
        super().__init__(parent)
        self._key = section_key
        self._cfg = SECTION_CONFIG[section_key]

        self.title(self._cfg["title"])
        self.geometry("740x420")
        self.minsize(500, 300)
        self.resizable(True, True)

        self._build()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(parent)
        self.focus_set()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Create the treeview, scrollbar, and button row."""
        # --- Treeview + scrollbar ---
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=_PAD, pady=(_PAD, 0))

        cols = self._cfg["columns"]
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="browse"
        )
        col_w = max(100, 720 // len(cols))
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=col_w, anchor="w", minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Double-click opens edit dialog
        self._tree.bind("<Double-1>", lambda _e: self._edit())

        # --- Buttons ---
        btn_row = tk.Frame(self)
        btn_row.pack(fill="x", padx=_PAD, pady=_PAD)

        tk.Button(btn_row, text="Add New",  width=12,
                  command=self._add).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Edit",     width=10,
                  command=self._edit).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Delete",   width=10,
                  command=self._delete).pack(side="left")
        tk.Button(btn_row, text="Close",    width=10,
                  command=self.destroy).pack(side="right")

    # ------------------------------------------------------------------
    # Treeview helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Reload data from disk and repopulate the treeview."""
        for iid in self._tree.get_children():
            self._tree.delete(iid)
        net_data = data_module.load_data()
        for entry in CRUD[self._key]["list"](net_data):
            values = tuple(str(entry.get(k, "")) for _, k, _ in self._cfg["fields"])
            self._tree.insert("", "end", values=values)

    def _selected_dict(self) -> dict[str, Any] | None:
        """Return the selected row as a dict, or None if nothing is selected."""
        sel = self._tree.selection()
        if not sel:
            return None
        values = self._tree.item(sel[0], "values")
        entry: dict[str, Any] = {}
        for i, (_, key, type_str) in enumerate(self._cfg["fields"]):
            raw = values[i] if i < len(values) else ""
            entry[key] = int(raw) if type_str == "int" and raw.lstrip("-").isdigit() else raw
        return entry

    # ------------------------------------------------------------------
    # CRUD handlers
    # ------------------------------------------------------------------

    def _add(self) -> None:
        """Open an Add dialog; save on confirm, do nothing on cancel."""
        dialog = EntryDialog(
            self,
            f"Add {self._cfg['singular']}",
            self._cfg["fields"],
        )
        if dialog.result is None:
            return
        net_data = data_module.load_data()
        try:
            CRUD[self._key]["add"](net_data, dialog.result)
            data_module.save_data(net_data)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._refresh()

    def _edit(self) -> None:
        """Open an Edit dialog for the selected row; save on confirm."""
        current = self._selected_dict()
        if current is None:
            messagebox.showinfo(
                "No Selection", "Please select an entry to edit.", parent=self
            )
            return

        dialog = EntryDialog(
            self,
            f"Edit {self._cfg['singular']}",
            self._cfg["fields"],
            initial_values=current,
        )
        if dialog.result is None:
            return

        net_data = data_module.load_data()
        id_field = IDENTITY_FIELD[self._key]
        old_key_val = current[id_field]

        # Guard: reject primary-key change that would collide with another entry
        new_key_val = dialog.result[id_field]
        if new_key_val != old_key_val:
            duplicate = any(
                e[id_field] == new_key_val
                for e in net_data[self._key]
            )
            if duplicate:
                messagebox.showerror(
                    "Duplicate Entry",
                    f"An entry with {id_field} = '{new_key_val}' already exists.",
                    parent=self,
                )
                return

        idx = data_module.find_entry_index(net_data[self._key], id_field, old_key_val)
        if idx is None:
            messagebox.showerror(
                "Error",
                "Entry not found — it may have been deleted externally.",
                parent=self,
            )
            self._refresh()
            return

        CRUD[self._key]["update"](net_data, idx, dialog.result)
        data_module.save_data(net_data)
        self._refresh()

    def _delete(self) -> None:
        """Delete the selected row after a confirmation prompt."""
        current = self._selected_dict()
        if current is None:
            messagebox.showinfo(
                "No Selection", "Please select an entry to delete.", parent=self
            )
            return

        id_field = IDENTITY_FIELD[self._key]
        identifier = current.get(id_field, "this entry")
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{identifier}'?",
            parent=self,
        ):
            return

        net_data = data_module.load_data()
        idx = data_module.find_entry_index(net_data[self._key], id_field, identifier)
        if idx is None:
            messagebox.showerror("Error", "Entry not found.", parent=self)
            self._refresh()
            return

        CRUD[self._key]["delete"](net_data, idx)
        data_module.save_data(net_data)
        self._refresh()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class NetDocApp:
    """Root window for the NetDoc GUI application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NetDoc — Network Documentation")
        self.root.resizable(False, False)
        # Track open section windows to avoid duplicates
        self._open_wins: dict[str, SectionWindow] = {}
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Lay out the main window."""
        outer = tk.Frame(self.root, padx=_PAD * 3, pady=_PAD * 2)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer, text="NetDoc",
            font=("Arial", 20, "bold"),
        ).pack(pady=(0, 2))
        tk.Label(
            outer, text="Network Documentation Manager",
            font=("Arial", 10),
        ).pack(pady=(0, _PAD * 2))

        section_buttons = [
            ("VLANs",        "vlans"),
            ("Servers",      "servers"),
            ("Switches",     "switches"),
            ("DHCP Scopes",  "dhcp_scopes"),
        ]
        for label, key in section_buttons:
            tk.Button(
                outer, text=label, width=_BTN_W,
                command=lambda k=key: self._open_section(k),
                pady=5,
            ).pack(pady=4)

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(_PAD, 4))

        tk.Button(
            outer, text="Export Documentation", width=_BTN_W,
            command=self._export,
            pady=5,
        ).pack(pady=4)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _open_section(self, section_key: str) -> None:
        """Open the section window, or bring it to front if already open."""
        existing = self._open_wins.get(section_key)
        if existing and existing.winfo_exists():
            existing.lift()
            existing.focus_set()
            return
        win = SectionWindow(self.root, section_key)
        self._open_wins[section_key] = win

    def _export(self) -> None:
        """Export HTML and Markdown to the user's Documents folder with no file prompt."""
        docs_dir = _get_documents_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)

        try:
            net_data = data_module.load_data()
            export_html(net_data, str(docs_dir / "network_docs.html"))
            export_markdown(net_data, str(docs_dir / "network_docs.md"))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Export Failed", str(exc), parent=self.root)
            return

        messagebox.showinfo(
            "Export Successful",
            "Document Successfully Exported to Documents",
            parent=self.root,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Initialise Tk and start the NetDoc GUI event loop."""
    root = tk.Tk()
    NetDocApp(root)
    root.mainloop()
