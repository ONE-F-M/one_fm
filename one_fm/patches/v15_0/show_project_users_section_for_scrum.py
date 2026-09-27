"""Show the "Project Manager and Users" section on SCRUM projects.

The `users_section` (a standard Project field) was only shown for External and
Internal projects, but `users` is mandatory for SCRUM and Personal projects too
— so the required field was hidden. This re-applies the Project property setters
from the source of truth in one_fm.custom.property_setter.project.

make_property_setter upserts, so this is idempotent.

Note: on sites where this already ran, it will not run again. The corrected
conditions (SCRUM matched on the controlled `doc.type`, plus 'Personal Project')
are re-applied by backfill_project_sprint_prefix.
"""

from one_fm.custom.property_setter.project import get_project_properties
from one_fm.setup.setup import add_property_setter


def execute():
    add_property_setter(get_project_properties())
