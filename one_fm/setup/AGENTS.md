# Setup Module

Owner: Development team
Path: `one_fm/one_fm/setup/`

## Purpose

Contains install-time setup hooks that run after `bench install-app one_fm`. Manages the programmatic creation of custom fields, property setters, workflows, and assignment rules for standard Frappe/ERPNext DocTypes.

## Key Files

- `setup.py` — main setup entry point (`after_install` hook)
- `custom_field.py` — defines all custom fields added to standard DocTypes (14KB)
- `property_setter.py` — modifies properties of existing fields on standard DocTypes (11KB)
- `workflow.py` — creates workflows for DocTypes (8KB)
- `assignment_rule.py` — creates assignment rules (10KB)

## How Setup Works

1. `hooks.py` registers `after_install = "one_fm.setup.setup.after_install"`
2. `after_install()` calls functions from the other setup files to create:
   - Custom fields on standard DocTypes (Employee, Sales Invoice, Purchase Order, etc.)
   - Property setters to modify field labels, visibility, mandatory status
   - Workflows for approval chains
   - Assignment rules for automatic task routing

## Conventions

1. **Use the `add-custom-fields` skill** for adding new custom fields.
2. **Use the `add-property-setter` skill** for modifying field properties.
3. **Custom fields use `create_custom_fields()`** from `frappe.custom.doctype.custom_field.custom_field`.
4. **Property setters use `make_property_setter()`** from `frappe.custom.doctype.property_setter.property_setter`.
5. **Never modify standard DocType JSON files.** Always use programmatic setup.

## Cross-Module Dependencies

- **hooks.py**: `after_install` hook points here
- **custom/**: Contains the generated custom field, property setter, workflow, and assignment rule JSON exports
- **patches/**: Patches may add custom fields/property setters incrementally (setup runs only on fresh install)

## Testing

Setup hooks are tested during `bench install-app one_fm`. To re-run setup manually:

```bash
bench execute one_fm.setup.setup.after_install
```
