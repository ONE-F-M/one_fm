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
| `one_fm/api/api.py` | Removed imports from removed `frappe.desk.page.user_profile` and `frappe.social.doctype.energy_point_log` |
| `one_fm/permissions.py` | Added `frappe.db.exists("DocType", "Energy Point Log")` guard in `get_point_logs()` |
| `one_fm/__init__.py` | Bumped `__version__` to `16.0.0`, removed `from __future__` import |
| `one_fm/api/api.py` | Replaced `get_user_rank()` and `get_user_energy_and_review_points()` calls with fallback `"0"` values |

## Summary of Breaking Changes (Frappe v15 → v16)

| Feature | v15 | v16 | Impact |
|---------|-----|-----|--------|
| `frappe.desk.page.user_profile` | Exists | **Removed** | Direct import in `api.py` |
| `frappe.social.doctype.energy_point_log` | Exists | **Removed** | Direct import in `api.py` |
| `Energy Point Log` doctype | Exists | **Removed** | Query in `permissions.py` |
| `google-protobuf` metaclass API | v4.x works | v4.x **broken** on Python 3.14 | Requires protobuf >=5.x and matching google cloud libs |
| `from __future__` imports | Works | Works (no-op) | Cleanup only (623 files) |
| Python version | 3.10-3.13 | 3.10+ | Constraint in pyproject.toml |

## Notes for Other Devs

### Migration Blueprint

1. **Clone to new bench**: Clone the app, create a `version-16-fixes` branch from `staging`
2. **Update `pyproject.toml`**: Bump `frappe-dependencies` and Python version constraints
3. **Fix removed module imports**: `frappe.desk.page.user_profile` and `frappe.social` were removed in v16
4. **Guard removed doctype queries**: Use `frappe.db.exists()` before querying removed DocTypes
5. **Update Google Cloud dependencies**: Python 3.14 requires protobuf >=5.x, which requires upgraded google-cloud-* libraries
6. **Remove `from __future__`**: Cosmetic cleanup (623 occurrences)
7. **Bump version**: Update `__version__` in `__init__.py`
8. **Test**: Create a site, install apps, run patches, verify core flows
