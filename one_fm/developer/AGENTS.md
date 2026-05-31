# Developer Module

Owner: Development team
Path: `one_fm/one_fm/developer/`

## Purpose

Contains internal developer tooling: DMARC email authentication processing, admin activity logging, bug tracking (Bug Buster), file transfer utilities, and application release notes.

## Key DocTypes

### Bug Buster
- **Bug Buster** / **Bug Buster Employee** / **Bug Buster Employee Detail** / **Bug Buster GitHub Detail** / **Bug Buster Issue Detail** / **Bug Buster Report** — internal bug tracking system with GitHub integration. `roster_bug_buster` runs daily to check for roster-related bugs.

### Admin Logging
- **Administrator Activity Log** / **Administrator Auto Log** / **Administrator Log Action** — tracks administrator actions for audit trails

### Email Security
- **DMARC Record** / **DMARC Report** — DMARC email authentication report processing (uses `dmarc_processor.py`)

### Other
- **Application Release Notes** — tracks app version releases
- **File Transfer Wizard** — bulk file transfer utility

## Key Files

- `dmarc_processor.py` — parses and processes DMARC aggregate reports

## Scheduler Events

| Schedule | Method | Purpose |
|---|---|---|
| Daily | `bug_buster.roster_bug_buster` | Daily roster bug detection |

## Testing

```bash
bench run-tests --module one_fm.developer
```
