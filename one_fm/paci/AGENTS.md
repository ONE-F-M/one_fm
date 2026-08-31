# PACI Module

Owner: GRD team
Path: `one_fm/one_fm/paci/`

## Purpose

Manages PACI (Public Authority for Civil Information) signature assignments for authorized signatories. This is a small, focused module that complements the main GRD module's PACI document handling.

## Key DocTypes

- **PACI Signature** — records of PACI signature authorizations
- **PACI Signature Assignment** — child table linking signatures to specific authorization contexts

## Relationship to GRD

The main PACI civil ID tracking DocTypes (`PACI`, `PACI Number`) live in the `grd/` module. This module handles only the signature authorization aspect.

## Testing

```bash
bench run-tests --module one_fm.paci
```
