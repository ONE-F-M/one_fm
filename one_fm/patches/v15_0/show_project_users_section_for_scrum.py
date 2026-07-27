"""Show the "Project Manager and Users" section on SCRUM projects.

The `users_section` (a standard Project field) was only shown for External and
Internal projects, but `users` is mandatory for SCRUM projects too — so the
required field was hidden. This re-applies the Project property setters (the
source of truth in one_fm.custom.property_setter.project), whose `users_section`
depends_on now also includes 'SCRUM Project'.

make_property_setter upserts, so this is idempotent.
"""

from one_fm.custom.property_setter.project import get_project_properties
from one_fm.setup.setup import add_property_setter


def execute():
    add_property_setter(get_project_properties())
