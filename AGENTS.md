# AGENTS.md

This repository is the ONE-FM custom Frappe app. It targets Frappe/ERPNext/HRMS version 15 and follows the branch flow `staging -> test-production -> version-15`.

## Stack
- Frappe v15
- ERPNext v15
- HRMS v15
- Python 3.10+
- MariaDB
- Redis

## Repository layout
- `one_fm/api/`: whitelisted API endpoints and API helpers
- `one_fm/operations/`: operations and scheduling domain
- `one_fm/hiring/`: hiring and onboarding domain
- `one_fm/grd/`: government relations domain
- `one_fm/permissions.py`: permission helpers and permission query conditions
- `one_fm/one_fm/doctype/`: core doctypes
- `one_fm/patches/`: schema and data migration patches

## Frappe conventions
- Keep business logic in controller methods or well-named service functions.
- Use hooks instead of patching framework code directly where possible.
- Validate permissions before data access.
- Prefer Query Builder or ORM over raw SQL unless performance requires otherwise.
- Background work should use `frappe.enqueue`.

## hooks.py guidance
Common hook areas in this repo:
- `doc_events`
- `scheduler_events`
- `permission_query_conditions`
- `has_permission`
- `override_whitelisted_methods`

When changing hooks, check for side effects across mobile APIs, scheduled jobs, and doctypes that share utility functions.

## DocType lifecycle
Most DocType logic belongs in:
- `validate`
- `before_save`
- `on_update`
- `before_submit`
- `on_submit`
- `on_cancel`

Avoid putting heavy business logic into client scripts when the server should enforce the rule.

## Branch and PR workflow
- Create feature branches from `staging`
- Open PRs into `staging`
- After validation, changes flow into `test-production`
- Production releases land in `version-15`

Never bypass this flow for normal application work.

## Tests
Run tests from bench:
```bash
bench --site <site> run-tests --app one_fm --failfast
```

Useful narrower patterns:
```bash
bench --site <site> run-tests --doctype "Operations Shift"
bench --site <site> run-tests --module one_fm.operations
```

## Key dependencies
- `frappe`
- `erpnext`
- `hrms`

Be careful when changing code paths that are used before ERPNext or HRMS install hooks finish.

## Module boundaries
- `operations`: rostering, shifts, attendance, contracts, field operations
- `hiring`: applicants, onboarding, recruitment pipeline
- `grd`: work permits, residency, compliance documents
- `api`: whitelisted methods, mobile endpoints, payload validation
- `permissions`: access control and filtering rules
- `legal`: penalties, investigations, legal workflows
- `accommodation`: employee housing, buildings, units, occupancy

## Commit format
Use conventional commits:
- `feat(scope): subject`
- `fix(scope): subject`
- `chore(scope): subject`
- `docs(scope): subject`
- `ci(scope): subject`
- `refactor(scope): subject`
- `test(scope): subject`

## Agent working rules
- Do not assume a DocType exists, verify it first.
- Do not change migration-sensitive data structures without checking patches.
- Document any risky assumption in the PR description.
- Keep changes scoped to the work item branch.
