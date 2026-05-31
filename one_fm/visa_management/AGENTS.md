# Visa Management Module

Owner: GRD / HR team
Path: `one_fm/one_fm/visa_management/`

## Purpose

Manages employee visa requests for travel purposes. This module handles the visa request workflow, distinct from the work permit and residency flows in the GRD module.

## Key DocTypes

- **Visa Request** — employee visa request for business or personal travel, including destination, duration, and document requirements

## Relationship to GRD

Work visas (work permits, residency) are managed in the `grd/` module. This module focuses on travel visa requests. Related DocTypes like `Visa Stamping` and `Visa Type` live in the `one_fm/one_fm/` core module.

## Testing

```bash
bench run-tests --module one_fm.visa_management
```
