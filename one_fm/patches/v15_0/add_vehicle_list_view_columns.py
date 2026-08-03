import json

import frappe

from one_fm.custom.property_setter.vehicle import get_vehicle_properties
from one_fm.setup.setup import add_property_setter

# The Vehicle list view as configured in production, which every environment is
# brought in line with (WI-001765). The saved List View Settings row wins over the
# DocField in_list_view flags, so the columns are pinned here in the same order.
PRODUCTION_COLUMNS = [
    {"fieldname": "name", "label": "ID"},
    {"fieldname": "license_plate", "label": "License Plate"},
    {"fieldname": "fuel_type", "label": "Fuel Type"},
    {"fieldname": "uom", "label": "Fuel UOM"},
    {"fieldname": "model", "label": "Model"},
    {"fieldname": "vehicle_value", "label": "Vehicle Value"},
]
TOTAL_FIELDS = "7"


def execute():
    """Show the License Plate instead of the Odometer in the Vehicle list view.

    Two parts, because Frappe resolves list columns from two places:
      1. The in_list_view property setters, which decide the candidate columns.
      2. The List View Settings row, which pins the order and, when present,
         overrides the flags entirely - so a site holding a stale row would keep
         showing the Odometer no matter what the setters say.
    """
    add_property_setter(
        [p for p in get_vehicle_properties() if p.get("property") == "in_list_view"]
    )

    settings = (
        frappe.get_doc("List View Settings", "Vehicle")
        if frappe.db.exists("List View Settings", "Vehicle")
        else frappe.new_doc("List View Settings")
    )
    if settings.is_new():
        settings.name = "Vehicle"

    settings.fields = json.dumps(PRODUCTION_COLUMNS)
    settings.total_fields = TOTAL_FIELDS
    settings.save(ignore_permissions=True)
