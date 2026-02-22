# Code Review — NetDoc Network Documentation Generator

**Reviewer:** Senior Python / Security Review
**Date:** 2026-02-21
**Files reviewed:** `main.py`, `modules/cli.py`, `modules/data.py`, `modules/export.py`
**Scope:** Security, code quality, logic correctness, dependencies, and credential guard integrity

---

## Summary Ratings

| Area | Rating | Notes |
|---|---|---|
| Security | **WARN** | No credential data found; path handling and input validation gaps exist |
| Code Quality | **PASS** | Well-structured, consistently documented, good use of TypedDicts |
| Logic Bugs | **WARN** | `find_entry_index` returning `None` is not guarded against at call sites |
| Dependency Review | **PASS** | Minimal, all stdlib or `rich`; no network calls, no eval/exec |
| Credential Guard | **WARN** | Keyword list has gaps; heuristic has documented bypass vectors |

---

## 1. Security — WARN

### 1.1 No credential data detected in any file

No passwords, tokens, secrets, API keys, or community strings appear anywhere in the source. The tool is clean in this regard.

---

### 1.2 `data/network.json` path is relative — `data.py:9`

```python
DATA_FILE = "data/network.json"
```

The data file path is resolved at runtime relative to the **current working directory**, not the script's location. If the tool is invoked from a different directory (e.g., via a scheduled task or a shortcut), data will be written to — or read from — a different location, potentially silently creating a second empty database.

**Fix:** Resolve the path relative to the module file using `pathlib`:

```python
from pathlib import Path
DATA_FILE = Path(__file__).parent.parent / "data" / "network.json"
```

---

### 1.3 `save_data` is not atomic — `data.py:78–82`

```python
with open(DATA_FILE, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
```

Writing directly to the live file means a crash, power loss, or `KeyboardInterrupt` mid-write will leave a corrupted or zero-byte `network.json`. There is no backup and no recovery path.

**Fix:** Write to a `.tmp` file alongside the target, then use `os.replace()` (atomic on both POSIX and Windows NTFS):

```python
import tempfile
tmp = DATA_FILE + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
os.replace(tmp, DATA_FILE)
```

---

### 1.4 No schema validation on `load_data` — `data.py:70–75`

```python
with open(DATA_FILE, "r", encoding="utf-8") as fh:
    return json.load(fh)
```

If `network.json` is manually edited and the structure is wrong (missing a top-level key, wrong types, extra unexpected fields), the error surfaces as an unhelpful `KeyError` or `TypeError` deep inside a display or CRUD function — not at load time.

**Fix:** After loading, verify the four required keys exist and are lists:

```python
required_keys = {"vlans", "servers", "switches", "dhcp_scopes"}
if not required_keys.issubset(loaded.keys()):
    raise ValueError(f"network.json is missing required keys: {required_keys - loaded.keys()}")
```

---

### 1.5 VLAN ID range not enforced — `cli.py:228`

```python
vlan_id = IntPrompt.ask("  VLAN ID (1–4094)")
```

`IntPrompt` enforces that input is an integer, but does not enforce the 1–4094 range stated in the prompt. A user can enter `0`, `-1`, or `9999` and it will persist to disk without complaint.

**Fix:** Add a loop with an explicit range check after the prompt.

---

### 1.6 IP address fields accept arbitrary strings — `cli.py:239,249,260,261`

Fields labelled "IP address", "Gateway", and "DNS" accept any string. There is no format validation (IPv4, CIDR, hostname). A typo like `10.0.1` or `10.0.1.999` will save silently and appear in all exports.

**Risk level:** Low for a local CLI tool, but it undermines the documentation's reliability — which is the entire point.

**Fix:** Add a lightweight validation helper using `ipaddress` from the stdlib (no new dependency):

```python
import ipaddress

def is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
```

---

### 1.7 Rich markup injection via user input — `cli.py` (multiple sites)

Rich interprets bracket notation as markup. User-supplied strings are interpolated directly into `console.print()` f-strings in several places:

```python
# cli.py:369
if not Confirm.ask(f"  Delete VLAN {selected['id']} ({selected['name']})?"):
```

If a VLAN `name` contains Rich markup (e.g., `[bold red]`), it will be rendered — not displayed literally. This is cosmetic only but worth eliminating.

**Fix:** Use Rich's `escape()` utility on any user-supplied string before interpolating it into a markup string:

```python
from rich.markup import escape
Confirm.ask(f"  Delete VLAN {selected['id']} ({escape(selected['name'])})?")
```

---

### 1.8 No file locking — `data.py`

Two simultaneous instances of the tool will race on read/write access to `network.json`. The last writer wins and silently discards the other's changes. This is unlikely in a single-user CLI context but is worth noting if the tool ever runs unattended or via scripts.

---

## 2. Code Quality — PASS

The codebase is genuinely well-written. Functions are short, docstrings are present on all public symbols, and type hints are used consistently. The items below are refinements, not structural problems.

---

### 2.1 `Optional[int]` vs `int | None` — `cli.py:117`, `data.py:89`

```python
def pick_entry(count: int, noun: str = "entry") -> Optional[int]:
def find_entry_index(...) -> Optional[int]:
```

Both files use `from __future__ import annotations` at the top and target Python 3.10+. The `Optional[T]` form is legacy spelling. The idiomatic modern form is `int | None`. Mixing both styles in a 3.10+ project is inconsistent.

---

### 2.2 `NetworkData` is duplicated — `data.py:52–58` vs `export.py:19`

`data.py` defines a proper `TypedDict`:
```python
class NetworkData(TypedDict):
    vlans: list[Vlan]
    ...
```

`export.py` defines its own looser alias:
```python
NetworkData = dict[str, list[dict[str, Any]]]
```

These are incompatible at the type-checker level. `export.py` should import `NetworkData` from `data.py` rather than redefining it.

---

### 2.3 Private table-builder functions have no return type annotation — `export.py:69–102`

`_vlans_md`, `_servers_md`, `_switches_md`, `_dhcp_md` (and their HTML counterparts) all lack `-> str` return type annotations. Every other function in the module is annotated. These are an oversight.

---

### 2.4 Repetitive table-builder structure — `export.py`

Eight functions (`_vlans_md`, `_vlans_html`, `_servers_md`, etc.) follow identical structure with only the field names and headers differing. This is copy-paste code. A table configuration approach would reduce the module by ~60 lines and eliminate the risk of divergent bugs between the MD and HTML paths.

This is not a bug — it is a maintainability observation. Out of scope for an immediate fix but worth addressing before the codebase grows.

---

### 2.5 `run()` does not handle startup exceptions gracefully — `cli.py:668–678`

```python
def run() -> None:
    ...
    data = load_data()
    main_menu(data)
```

If `load_data()` raises (corrupted JSON, permission denied, disk full), the exception propagates as an unhandled traceback to the user. The tool should catch `json.JSONDecodeError`, `OSError`, and `ValueError` at startup and print a human-readable message.

---

## 3. Logic Bugs — WARN

### 3.1 `find_entry_index` returning `None` is not checked at call sites — `cli.py:351,371,419,439,485,505,552,572`

`find_entry_index` is documented to return `Optional[int]`:

```python
def find_entry_index(entries: list[Any], key: str, value: Any) -> Optional[int]:
    ...
    return None  # if not found
```

Every call site in `cli.py` passes the result directly as an index with no guard:

```python
# cli.py:351–353
real_idx = find_entry_index(data["vlans"], "id", selected["id"])
update_vlan(data, real_idx, updates)  # real_idx could be None
save_data(data)
```

Under normal use this won't trigger — the entry was just displayed, so it must exist. But if the data file is externally modified between the display and the write, or a future refactor introduces a sort-copy bug, `data["vlans"][None]` raises an unhelpful `TypeError`.

**Fix:** Assert or guard at each call site:

```python
real_idx = find_entry_index(data["vlans"], "id", selected["id"])
if real_idx is None:
    console.print("[red]  Error: Entry no longer exists. Was the data file modified externally?[/red]")
    return
```

---

### 3.2 Markdown table breaks on pipe characters in cell values — `export.py:60–66`

```python
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    ...
    "| " + " | ".join(str(cell) for cell in row) + " |"
```

If any field value contains a `|` character (valid in notes like "Primary | Backup"), it will be interpreted as a column delimiter and break the table structure in all Markdown renderers.

**Fix:** Escape pipes in cell values:

```python
str(cell).replace("|", "\\|")
```

---

### 3.3 `load_data` swallows all JSON errors silently — `data.py:70–75`

```python
with open(DATA_FILE, "r", encoding="utf-8") as fh:
    return json.load(fh)
```

A `json.JSONDecodeError` (from a truncated write) propagates as a raw traceback. There is no recovery path and no message telling the user which file is corrupt or what to do about it.

---

### 3.4 `delete_vlan`/`delete_server` etc. pass unvalidated index — `data.py:113–115`

```python
def delete_vlan(data: NetworkData, index: int) -> None:
    data["vlans"].pop(index)
```

If `index` is `None` (see 3.1), this raises `TypeError`. If `index` is out of bounds, it raises `IndexError`. Neither is caught. The functions should either validate the index or callers must guarantee it is not `None`.

---

## 4. Dependency Review — PASS

| Library | Use | Verdict |
|---|---|---|
| `rich` | Terminal formatting, tables, prompts | Appropriate. Well-maintained, no transitive vulnerabilities of concern. |
| `json` | stdlib | Appropriate |
| `os` | stdlib | Appropriate |
| `re` | stdlib | Appropriate |
| `datetime` | stdlib | Appropriate |
| `pathlib` | stdlib | Not yet used — should replace `os.path` in data.py |
| `ipaddress` | stdlib | Not yet used — recommended for IP validation |
| `pytest` | Test runner | Appropriate, dev-only dependency |

No `subprocess`, no `eval`, no `exec`, no network requests, no external API calls. The dependency surface is minimal and appropriate.

---

## 5. Credential Guard Analysis — WARN

### 5.1 Keyword regex is sound but incomplete — `cli.py:47–50`

```python
_CREDENTIAL_KEYWORDS = re.compile(
    r"\b(password|passwd|secret|credential|api[_\-]?key|auth[_\-]?token|private[_\-]?key)\b",
    re.IGNORECASE,
)
```

**Covered:** `password`, `passwd`, `secret`, `credential`, `api_key`, `api-key`, `apikey`, `auth_token`, `auth-token`, `authtoken`, `private_key`, `private-key`, `privatekey`

**Not covered — notable gaps for a network context:**

| Missing keyword | Why it matters |
|---|---|
| `community` | SNMP community strings (e.g., "community: public") |
| `preshared` / `psk` | WPA2/VPN pre-shared keys |
| `enable` | Cisco `enable` password is a common accident |
| `passphrase` | SSH key passphrases |
| `token` | Bare "token" without "auth_" prefix |
| `private` | Bare "private" — `private_key` is caught, but "private" alone is not |

---

### 5.2 Heuristic has exploitable gaps — `cli.py:64–72`

```python
if len(value) >= 8:
    has_upper = bool(re.search(r"[A-Z]", value))
    has_lower = bool(re.search(r"[a-z]", value))
    has_digit = bool(re.search(r"\d", value))
    has_special = bool(re.search(r"[!@#$%^&*=+;'\",<>?\\|`~]", value))
    if all([has_upper, has_lower, has_digit, has_special]):
        return True
```

The heuristic requires **all four** character classes simultaneously. Any credential that doesn't meet all four criteria bypasses the check silently:

| Credential | Caught? | Reason |
|---|---|---|
| `Cisco123` | No | No special character |
| `winter2024!` | No | No uppercase |
| `P@ssword` | No | No digit |
| `cisco` | No | Under 8 characters |
| `r3adOnly!` | No | No uppercase |
| `P@ssw0rd!` | **Yes** | All four classes present |

These are realistic credentials someone might actually type into a "Notes" or "Uplink" field. The heuristic catches generated passwords well but misses many human-chosen passwords.

**Suggested additions:** Add `passphrase`, `community`, `psk`, `enable`, `token` to the keyword list. Consider lowering the heuristic requirement from "all four" to "any three" to widen the net, accepting a small increase in false positives.

---

### 5.3 `safe_edit_prompt` intentional bypass is documented and acceptable — `cli.py:109–110`

```python
if value == current:
    return value  # unchanged — skip credential check
```

This is correct behavior. If a previously stored value happens to match the heuristic (which should not occur under normal use, since all additions go through `safe_prompt`), editing and pressing Enter would silently retain it. The inline comment documents this. The risk is low and acceptable.

---

### 5.4 Credential guard is consistently applied — PASS

Every user-facing text input goes through either `safe_prompt()` or `safe_edit_prompt()`. There is no field that bypasses the guard. The four `prompt_new_*` and four `prompt_edit_*` functions all route every field through one of these two helpers. The guard architecture is sound.

---

## Prioritized Fix List

The following items should be resolved before this tool is distributed or used in a production district environment, ordered by risk:

### Critical (data integrity / data loss risk)

1. **[data.py:78]** Make `save_data` atomic using a temp file + `os.replace()`. A crash during write corrupts the database.
2. **[data.py:70]** Wrap `json.load` in a `try/except json.JSONDecodeError` with a clear user message and recovery instructions.
3. **[cli.py — 8 sites]** Check the return value of `find_entry_index` before using it as an index. A `None` result currently causes a `TypeError` with no useful context.

### High (correctness / trust)

4. **[data.py:70]** Validate the schema of loaded JSON (required keys, correct types) before returning. Detect and report manual edits that break structure.
5. **[export.py:63]** Escape pipe characters `|` in Markdown table cell values to prevent broken table formatting.
6. **[data.py:9]** Change `DATA_FILE` to an absolute path anchored to the script location using `pathlib.Path`.

### Medium (security / usability)

7. **[cli.py:47]** Extend `_CREDENTIAL_KEYWORDS` to include `community`, `preshared`, `psk`, `passphrase`, `enable`, `token`.
8. **[cli.py:64]** Consider lowering the heuristic from requiring all four character classes to any three, to catch more human-chosen passwords.
9. **[cli.py:228]** Enforce VLAN ID range 1–4094 after the `IntPrompt` call.
10. **[cli.py:239,249,260,261]** Validate IP address fields against `ipaddress.ip_address()` from stdlib.
11. **[cli.py — multiple]** Escape Rich markup in user-supplied strings before interpolating into `console.print()` / `Confirm.ask()` calls using `rich.markup.escape()`.

### Low (code quality / maintainability)

12. **[export.py:19]** Remove the local `NetworkData` alias from `export.py` and import the canonical `NetworkData` TypedDict from `data.py`.
13. **[export.py:69–102]** Add `-> str` return type annotations to all private table-builder functions.
14. **[cli.py:668]** Wrap `load_data()` in `run()` with a `try/except` block to surface startup errors gracefully.
15. **[cli.py:117, data.py:89]** Replace `Optional[int]` with `int | None` to match Python 3.10+ idiomatic style.

---

*End of review.*

---

## Fixes Applied

**Applied:** 2026-02-22
**Pytest result:** 52/52 passed (Python 3.14.3)

Every item from the Prioritized Fix List was addressed. Items marked *not changed* are noted with rationale.

---

### Critical fixes

| # | Location | Issue | Resolution |
|---|---|---|---|
| 1 | `data.py:save_data` | Non-atomic write could corrupt `network.json` on crash | Rewrote to write a `.tmp` sibling file then `os.replace()` (atomic on POSIX and Windows NTFS) |
| 2 | `data.py:load_data` | `json.JSONDecodeError` propagated as a raw traceback | Wrapped `json.load` in `try/except`; re-raises `JSONDecodeError` with the file path and a recovery hint |
| 3 | `cli.py` — 8 sites | `find_entry_index` return value used as index with no `None` guard | Added `if real_idx is None: ... return` guard after every call to `find_entry_index` (edit and delete actions for all four entity types) |

---

### High-priority fixes

| # | Location | Issue | Resolution |
|---|---|---|---|
| 4 | `data.py:load_data` | No schema validation; bad JSON structure surfaced as confusing errors deep in CRUD code | After loading, checks `isinstance(loaded, dict)` and that all four required keys are present; raises `ValueError` with file path and recovery hint on failure. Two tests that documented the old (silent) behaviour were updated to assert the new `ValueError` |
| 5 | `export.py:_md_table` | Pipe `\|` in cell values broke Markdown table structure | Added `.replace("\|", "\\|")` to every cell value in `_md_table` |
| 6 | `data.py:DATA_FILE` | Relative path resolved against CWD, not the script's location | Changed to `Path(__file__).parent.parent / "data" / "network.json"` using `pathlib`; all I/O functions use `Path(DATA_FILE)` internally so tests can still monkeypatch with a string |

---

### Medium-priority fixes

| # | Location | Issue | Resolution |
|---|---|---|---|
| 7 | `cli.py:_CREDENTIAL_KEYWORDS` | Missing network-specific credential keywords | Extended regex to include `community`, `preshared`, `psk`, `passphrase`, `enable`, `token` |
| 8 | `cli.py:looks_like_credential` heuristic | Heuristic requiring all 4 character classes misses common human-chosen passwords | *Not changed.* The review says "Consider" (advisory). Lowering to any-3 would cause `AdminUser1234` to be flagged, breaking the existing test `test_accepts_long_string_missing_special` which documents a deliberate design choice. Noted for future review. |
| 9 | `cli.py:prompt_new_vlan` | VLAN ID range 1–4094 not enforced after `IntPrompt` | Added `while True:` loop with `1 <= vlan_id <= 4094` check and a clear error message |
| 10 | `cli.py:prompt_new_server/switch/dhcp_scope` | IP/gateway/DNS fields accepted arbitrary strings | Added `is_valid_ip()` helper (stdlib `ipaddress.ip_address()`); all four IP-type fields now loop until a valid address is entered. DNS accepts comma/space-separated multiple addresses |
| 11 | `cli.py` — multiple | User-supplied strings interpolated directly into Rich markup strings | Added `from rich.markup import escape`; applied `escape()` to all user-supplied names/hostnames in `console.print()` f-strings and `Confirm.ask()` prompts |

---

### Low-priority fixes

| # | Location | Issue | Resolution |
|---|---|---|---|
| 12 | `export.py` | Local `NetworkData = dict[...]` alias incompatible with `data.py` TypedDict | Removed local alias; now imports the canonical `NetworkData` TypedDict from `modules.data` |
| 13 | `export.py:69–102` | Private table-builder functions lacked `-> str` return annotations | Added `-> str` to all eight private functions (`_vlans_md`, `_servers_md`, `_switches_md`, `_dhcp_md`, `_vlans_html`, `_servers_html`, `_switches_html`, `_dhcp_html`) |
| 14 | `cli.py:run` | `load_data()` startup exceptions propagated as raw tracebacks | Wrapped `load_data()` in `try/except (json.JSONDecodeError, OSError, ValueError)` with a user-readable `[bold red]Cannot start:[/bold red]` message |
| 15 | `cli.py:117`, `data.py:89` | `Optional[int]` used instead of `int \| None` (Python 3.10+ style) | Changed both signatures to `int \| None`; removed `Optional` from `typing` imports in both files |

---

### Items acknowledged but not fixed

| Item | Reason not fixed |
|---|---|
| **1.8 File locking** | Single-user CLI tool; review itself categorises this as unlikely in normal use. No stdlib solution is fully cross-platform. |
| **2.4 Repetitive table builders** | Review explicitly says "Out of scope for an immediate fix." No bugs introduced — maintainability observation only. |
| **5.2 Heuristic — lower to any-3** | Advisory ("Consider"). Would flag normal infrastructure names containing no special character. Existing test `test_accepts_long_string_missing_special` covers this boundary deliberately. |
