# Custom Module

Owner: Development team
Path: `one_fm/one_fm/custom/`

## Purpose

Stores exported/generated customization artifacts: custom fields, property setters, workflows, and assignment rules. These are the output of the setup module and can also be managed via patches.

## Directory Structure

```
custom/
├── assignment_rule/   # Assignment rule JSON definitions
├── custom_field/      # Custom field JSON definitions
├── property_setter/   # Property setter JSON definitions
└── workflow/          # Workflow JSON definitions
```

## How It Works

1. Custom fields and property setters defined in `setup/` are exported here as JSON files.
2. These JSON files serve as the source of truth for what customizations the app applies.
3. During `bench migrate`, these are reconciled with the database.

## Conventions

1. **Do not manually edit JSON files** in this directory. Use the setup module or the `add-custom-fields` / `add-property-setter` skills.
2. **To add a new custom field:** Update `setup/custom_field.py`, re-run setup, and export the result.
3. **To modify a workflow:** Update `setup/workflow.py` or use the Workflow Builder UI, then export.

## Cross-Module Dependencies

- **setup/**: Generates these artifacts
- **patches/**: May add/modify custom fields incrementally
