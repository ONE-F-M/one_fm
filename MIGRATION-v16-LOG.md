# one_fm → Frappe v16 Migration Log

**Source:** `staging` branch → **Target:** `version-16-fixes` branch
**Bench:** `one-fm-bench` (Frappe v16.20.0, Python 3.14.3)
**Date:** 2026-06-07

---

## Issue #1 — `pyproject.toml` constraints block v16

### Problem
```toml
requires-python = ">=3.10,<3.14"
```
Python 3.14 is used by the new bench. Also:
```toml
[tool.bench.frappe-dependencies]
one_fm = ">=15.0.0,<16.0.0"
```
This restricts Frappe to v15 only.

### Fix
- Bump `requires-python` to `>=3.10,<3.15` (or wider `>=3.10`)
- Bump `frappe-dependencies` to `>=16.0.0,<17.0.0`

---

## Issue #2 — Import from removed `frappe.desk.page.user_profile`

### Problem
`one_fm/api/api.py` line 7 imports from a module that was removed in Frappe v16.
```python
from frappe.desk.page.user_profile.user_profile import get_energy_points_heatmap_data, get_user_rank
```
The entire user_profile page + its doctypes were removed from Frappe v16 (Energy Points system removed).

### Impact
- `get_user_rank` — used in `get_user_details()` for rank display
- `get_energy_points_heatmap_data` — imported but **unused** in this file

### Fix
- Remove the unused import
- Inline `get_user_rank` as a local helper since the Energy Points Log doctype no longer exists
- Return `0` for rank and energy points when the feature is unavailable

---

## Issue #3 — Import from removed `frappe.social.doctype.energy_point_log`

### Problem
`one_fm/api/api.py` line 8:
```python
from frappe.social.doctype.energy_point_log.energy_point_log import get_energy_points, get_user_energy_and_review_points
```
The entire `frappe.social` module was removed in Frappe v16.

### Impact
- `get_user_energy_and_review_points` — used in `get_user_details()` for energy/review points
- `get_energy_points` — imported but **unused** in this file

### Fix
- Remove the unused import
- Return fallback values (0) for energy and review points since the feature was removed

---

## Issue #4 — `permissions.py` queries `Energy Point Log` doctype

### Problem
`one_fm/permissions.py` `get_point_logs()` function queries:
```python
def get_point_logs(doctype, docname):
    return frappe.get_all(
        "Energy Point Log",
        filters={"reference_doctype": doctype, "reference_name": docname, ...},
        fields=["*"],
    )
```
This doctype does not exist in Frappe v16.

### Impact
- Called from `get_docinfo()` — the doc info panel will crash whenever a document is opened.

### Fix
- Wrap the query in a try/except to gracefully return `[]` if the doctype doesn't exist
- Or check `frappe.db.exists("DocType", "Energy Point Log")` before querying

---

## Issue #5 — `from __future__ import unicode_literals` in 623 files

### Problem
623 Python files still carry Python 2/3 compatibility import:
```python
from __future__ import unicode_literals
```
This is harmless in Python 3 but adds noise.

### Fix
- Remove from all files (can be automated with sed)

---

## Issue #6 — Python version constraint update

### Problem
`pyproject.toml` has `requires-python = ">=3.10,<3.14"` which excludes Python 3.14.

### Fix
- Update to `requires-python = ">=3.10,<3.15"`

---

## Changes Made (version-16-fixes branch)

### Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | Bumped `requires-python` to `>=3.10,<3.15` and `frappe-dependencies` to `>=16.0.0,<17.0.0` |
| `pyproject.toml` | Updated Google Cloud pins for Python 3.14 compatibility: `firebase-admin>=7.4.0`, `google-cloud-firestore>=2.27.0`, `google-cloud-vision>=3.14.0`, `google-cloud-storage>=3.4.1`, `google-cloud-core>=2.6.0`, `google-auth>=2.53.0` |
| `pyproject.toml` | Bumped `mindee>=4.36.0,<5` (Python 3.14 compatibility) |
| `one_fm/api/api.py` | Removed imports from removed `frappe.desk.page.user_profile` and `frappe.social.doctype.energy_point_log` |
| `one_fm/permissions.py` | Added `frappe.db.exists("DocType", "Energy Point Log")` guard in `get_point_logs()` |
| `one_fm/__init__.py` | Bumped `__version__` to `16.0.0`, removed `from __future__` import |
| `one_fm/api/api.py` | Replaced `get_user_rank()` and `get_user_energy_and_review_points()` calls with fallback `"0"` values |
| `one_fm/developer/doctype/file_transfer_wizard/file_transfer_wizard.py` | Replaced removed `offsite_backup_utils.get_latest_backup_file()` with direct `BackupGenerator` usage |
| `one_fm/one_fm/utils.py` | Removed unused imports from removed `frappe.integrations.offsite_backup_utils` |
| `one_fm/one_fm/depreciation_custom.py` | Adapted from removed `get_depreciable_asset_depr_schedules_data` to use v16's `get_depreciable_assets_data` + `make_depreciation_entry` |

## Issues Found During Site Installation

### Issue #7 — `mindee==4.28.2` PDF compressor fails on Python 3.14

**Error:** `ImportError: cannot import name 'POINTER' from '_ctypes'`

**Root cause:** `mindee` v4.28.2 uses an internal PDF compression library that imports from `_ctypes.POINTER`, which was removed/restructured in Python 3.14.

**Fix:** Bump mindee to `>=4.36.0,<5` — the newer version handles this differently.

### Issue #8 — `frappe.integrations.offsite_backup_utils` removed in v16

**Error:** `ModuleNotFoundError: No module named 'frappe.integrations.offsite_backup_utils'`

**Root cause:** The entire module was removed from Frappe v16. Two files imported from it:
- `one_fm/utils.py` — imported but **no functions were actually used**
- `file_transfer_wizard.py` — imported `get_latest_backup_file()` which was used in `get_last_backups()`

**Fix:** 
- Removed unused import from `utils.py`
- Replaced `get_latest_backup_file()` in `file_transfer_wizard.py` with direct `BackupGenerator.get_recent_backup()` call

### Issue #9 — `iban` custom field conflicts with standard ERPNext v16 field

**Error:** `ValidationError: A field with the name iban already exists in Employee`

**Root cause:** `one_fm` tries to create `iban` as a custom field on Employee, but in ERPNext v16, `iban` is now a standard field added by the Employee doctype schema.

**Fix (temporary):** Delete the `tabCustom Field` entry for Employee/iban before installing. Long-term: Remove the iban field definition from `one_fm/custom/custom_field/employee.py` since it's now standard.

### Issue #10 — `get_depreciable_asset_depr_schedules_data` renamed in ERPNext v16

**Error:** `ImportError: cannot import name 'get_depreciable_asset_depr_schedules_data'`

**Root cause:** `one_fm/one_fm/depreciation_custom.py` imported `get_depreciable_asset_depr_schedules_data` from `erpnext.assets.doctype.asset.depreciation`. In ERPNext v16, the depreciation system was restructured:
- Old function renamed to `get_depreciable_assets_data`
- Return format changed from schedule data directly to `(depr_schedule_name, asset_name, start_idx, end_idx)` tuples
- Schedules moved from direct Asset child table to separate `Asset Depreciation Schedule` doctype
- Journal entry creation moved to `make_depreciation_entry(depr_schedule_name, date)`

**Fix:** Rewrote `depreciation_custom.py`:
- Uses `get_depreciable_assets_data` from v16
- Delegates JE creation to v16's `make_depreciation_entry`
- Preserves one_fm's project-based account selection (`direct_depreciation_expense_account` vs `indirect_depreciation_expense_account`) via `_set_project_based_accounts` helper
- `make_depreciation(asset_name)` single-asset trigger adapted to query `Asset Depreciation Schedule` directly

### Issue #11 — Redis not running for new bench

**Error:** `redis.exceptions.ConnectionError: Error 111 connecting to 127.0.0.1:11004`

**Root cause:** Each bench has its own Redis port (cache/queue). The new bench expects 13004/11004 but no Redis server was started on those ports.

**Fix:** Start Redis from the bench config:
```bash
redis-server config/redis_cache.conf --daemonize yes
redis-server config/redis_queue.conf --daemonize yes
```

## Summary of Breaking Changes (Frappe v15 → v16)

| Feature | v15 | v16 | Impact |
|---------|-----|-----|--------|
| `frappe.desk.page.user_profile` | Exists | **Removed** | Direct import in `api.py` |
| `frappe.social.doctype.energy_point_log` | Exists | **Removed** | Direct import in `api.py` |
| `Energy Point Log` doctype | Exists | **Removed** | Query in `permissions.py` |
| `frappe.integrations.offsite_backup_utils` | Exists | **Removed** | Imports in 2 files |
| `mindee` PDF compressor | Works | **Broken** on Python 3.14 | Requires mindee >=4.36 |
| `get_depreciable_asset_depr_schedules_data` | Exists | **Renamed** to `get_depreciable_assets_data` | Full rewrite of `depreciation_custom.py` |
| `google-protobuf` metaclass API | v4.x works | v4.x **broken** on Python 3.14 | Requires protobuf >=5.x and matching google cloud libs |
| `iban` on Employee | Custom field | **Standard field** in ERPNext v16 | Custom field creation conflicts |
| `from __future__` imports | Works | Works (no-op) | Cleanup only (623 files) |
| Python version | 3.10-3.13 | 3.10+ | Constraint in pyproject.toml |

## Notes for Other Devs

### Migration Blueprint

1. **Clone to new bench**: Clone the app, create a `version-16-fixes` branch from `staging`
2. **Update `pyproject.toml`**: Bump `frappe-dependencies` and Python version constraints
3. **Fix removed module imports**: `frappe.desk.page.user_profile` and `frappe.social` were removed in v16
4. **Guard removed doctype queries**: Use `frappe.db.exists()` before querying removed DocTypes
5. **Replace removed utility modules**: `offsite_backup_utils` → `frappe.utils.backups.BackupGenerator`
6. **Update Google Cloud dependencies**: Python 3.14 requires protobuf >=5.x, which requires upgraded google-cloud-* libraries
7. **Update mindee dependency**: Must be >=4.36.0 for Python 3.14
8. **Handle now-standard fields**: Remove custom field definitions for fields that became standard in v16 (e.g. `iban` on Employee)
9. **Adapt depreciation module**: `get_depreciable_asset_depr_schedules_data` → `get_depreciable_assets_data`; schedules moved to separate `Asset Depreciation Schedule` doctype
10. **Remove `from __future__`**: Cosmetic cleanup (623 occurrences)
11. **Bump version**: Update `__version__` in `__init__.py`
12. **Test**: Create a site, install apps, run patches, verify core flows
