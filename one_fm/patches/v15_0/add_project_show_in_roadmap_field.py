"""Add the "Show in Roadmap" (custom_show_in_roadmap) custom field to Project.

A Select (blank / Yes / No) shown and required only for SCRUM projects
(depends_on / mandatory_depends_on eval:doc.type=="SCRUM"), inserted after the
Sprint Prefix field.

It is the opt-in flag for the frappe_agile Roadmap board (WI-002045): a SCRUM
project only gets a lane once this is Yes. Blank therefore keeps a project off
the board, which is deliberate - existing projects stay off until someone
curates them in, rather than the board showing everything as it did before.

The definition lives in one_fm.custom.custom_field.project (the source of
truth); this patch re-applies the full Project custom-field set with
update=True, so it is idempotent and also reconciles any drift in the other
Project fields.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.project import get_project_custom_fields


def execute():
    create_custom_fields(get_project_custom_fields(), update=True)
