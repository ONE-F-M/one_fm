# Patches Module

Owner: Development team
Path: `one_fm/one_fm/patches/`

## Purpose

Contains data migration patches organized by version. Patches run automatically during `bench migrate` and are registered in `one_fm/patches.txt`.

## Directory Structure

```
patches/
├── __init__.py
├── v0_12/     # Legacy patches
├── v1_0/      # v1.0 patches
├── v14_0/     # v14 migration patches
└── v15_0/     # v15 migration patches (current)
```

## How Patches Work

1. Create a new `.py` file in the appropriate version directory (e.g., `v15_0/my_patch.py`)
2. Implement an `execute()` function
3. Register the patch path in `one_fm/patches.txt`
4. Patches in `patches.txt` can be placed in `[pre_model_sync]` or `[post_model_sync]` sections

## Conventions

1. **Use the `create-patch` skill** for scaffolding new patches.
2. **pre_model_sync** patches run before DocType schema changes are applied — use for data that must exist before new required fields are added.
3. **post_model_sync** patches run after schema changes — use for data that depends on new fields/DocTypes.
4. **Never use raw SQL.** Use `frappe.qb`, `frappe.db.set_value`, or `frappe.get_doc()`.
5. **Batch large updates.** Use `create_batch()` for patches touching 1000+ records.
6. **Patches are one-shot.** They run once and are marked complete. To re-run, use `bench run-patch <path> --force`.

## Registration File

The patch registry is at `one_fm/patches.txt` (25KB, indicating many patches). Check this file before adding a new patch to avoid duplicate registration.

## Cross-Module Dependencies

- **patches.txt**: Must be updated when adding any new patch
- **setup/**: Install-time setup hooks may overlap with patch behavior
- **custom/**: Custom field and property setter patches

## Testing

Patches should be tested with `bench run-patch one_fm.patches.v15_0.my_patch --force` on a copy of production data.
