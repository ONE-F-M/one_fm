"""Make the mandatory "Sprint Prefix" field safe on existing SCRUM projects.

`add_project_sprint_prefix_field` introduced custom_sprint_prefix with
`mandatory_depends_on eval:doc.type=='SCRUM'` but left it empty, so every
pre-existing SCRUM project became unsaveable from the form — the client-side
mandatory check in frappe/public/js/frappe/form/save.js blocks the save even
for an unrelated edit such as changing a date.

This patch:

1. Re-applies the Project custom fields and property setters, so the corrected
   SCRUM conditions (matched on the controlled `doc.type`, not on the free-text
   Project Type record name) land on sites where the two 2026-07-23 patches
   have already run.
2. Resyncs Project.type from Project Type.type. `type` is a fetch_from field,
   so it is only written on save — rows saved before the Project Type got its
   `type` value still hold a stale one, and every condition above keys off it.
3. Fills custom_sprint_prefix for SCRUM projects that have none, deriving a
   short unique token from the project name.

The derived prefix is a starting point, not an answer: it is what shows up in
Sprint names (`<prefix>-001`) and as a lane on the Roadmap board, so the
generated values are logged for a human to review and override.

Idempotent: projects that already have a prefix are never touched.
"""

import re

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.project import get_project_custom_fields
from one_fm.custom.property_setter.project import get_project_properties
from one_fm.setup.setup import add_property_setter

# Dropped when abbreviating, so "Training and Reassessment" -> TR not TAR.
_STOPWORDS = {"a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "the", "to", "with"}

_MAX_PREFIX_LEN = 6

# Initialising a name can land on a word nobody wants in a Sprint title or on
# the Roadmap board — "Head Office Maintenance and Organization" abbreviates to
# HOMO. Anything here falls back to the first word instead. Not an exhaustive
# filter, which is part of why the patch logs every value it generates.
_AVOID = {"ASS", "CUM", "FAG", "HOMO", "TIT", "TITS", "WANK"}


def derive_sprint_prefix(project_name: str) -> str:
    """Return a short uppercase token derived from *project_name*.

    Multi-word names collapse to their initials ("Help Desk" -> HD); a name that
    is a single meaningful word is truncated instead ("Devops" -> DEVOPS), since
    a one-letter prefix would be useless in a Sprint name.
    """
    words = re.findall(r"[A-Za-z0-9]+", project_name or "")
    if not words:
        return ""

    meaningful = [w for w in words if w.lower() not in _STOPWORDS] or words

    if len(meaningful) == 1:
        token = meaningful[0]
    else:
        token = "".join(w[0] for w in meaningful)

    token = token[:_MAX_PREFIX_LEN].upper()
    if token in _AVOID:
        token = meaningful[0][:_MAX_PREFIX_LEN].upper()
    return token


def _unique_prefix(base: str, taken: set) -> str:
    """Return *base*, or *base* with a numeric suffix, not present in *taken*.

    Two projects sharing a prefix would interleave their sprint names and trip
    Sprint.validate_active_sprint_uniqueness, which allows only one Active
    sprint per prefix — so collisions have to be broken here.
    """
    if base and base not in taken:
        return base

    stem = (base or "PROJ")[: _MAX_PREFIX_LEN - 1]
    n = 2
    while f"{stem}{n}" in taken:
        n += 1
        if n > 99:  # pathological; fall back to something guaranteed free
            stem = (base or "PROJ")[: _MAX_PREFIX_LEN - 3]
            n = 2
    return f"{stem}{n}"


def _resync_project_type_values() -> int:
    """Copy Project Type.type onto Project.type where the two disagree."""
    rows = frappe.db.sql(
        """
        select p.name, pt.type as correct_type
        from `tabProject` p
        join `tabProject Type` pt on pt.name = p.project_type
        where ifnull(p.type, '') != ifnull(pt.type, '')
        """,
        as_dict=True,
    )
    for row in rows:
        frappe.db.set_value("Project", row.name, "type", row.correct_type, update_modified=False)
    return len(rows)


def execute():
    # 1. Corrected field + property-setter definitions.
    create_custom_fields(get_project_custom_fields(), update=True)
    add_property_setter(get_project_properties())

    # 2. `type` must be trustworthy before anything keys off it.
    resynced = _resync_project_type_values()
    if resynced:
        print(f"backfill_project_sprint_prefix: resynced Project.type on {resynced} project(s)")

    # 3. Backfill the now-mandatory prefix.
    taken = {
        (p.custom_sprint_prefix or "").strip().upper()
        for p in frappe.get_all(
            "Project",
            filters={"custom_sprint_prefix": ("is", "set")},
            fields=["custom_sprint_prefix"],
        )
    }
    taken.discard("")

    missing = frappe.get_all(
        "Project",
        filters={"type": "SCRUM", "custom_sprint_prefix": ("in", ["", None])},
        fields=["name", "project_name"],
        order_by="creation asc",
    )

    for project in missing:
        prefix = _unique_prefix(
            derive_sprint_prefix(project.project_name or project.name), taken
        )
        taken.add(prefix)
        frappe.db.set_value(
            "Project", project.name, "custom_sprint_prefix", prefix, update_modified=False
        )
        print(f"backfill_project_sprint_prefix: {project.name} -> {prefix}")

    if missing:
        print(
            f"backfill_project_sprint_prefix: set a prefix on {len(missing)} SCRUM project(s). "
            "Review them — the prefix appears in Sprint names and on the Roadmap board."
        )
