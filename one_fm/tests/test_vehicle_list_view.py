import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.property_setter.vehicle import get_vehicle_properties
from one_fm.patches.v15_0.add_vehicle_list_view_columns import (
    PRODUCTION_COLUMNS,
    TOTAL_FIELDS,
)


class TestVehicleListViewColumns(FrappeTestCase):
    """
    WI-001765: the Vehicle list view identifies a vehicle by its registration plate,
    not its odometer reading. Production was configured by hand; the property setters
    and the List View Settings row codify it for every environment.
    """

    def _in_list_view_setters(self):
        return {
            p["field_name"]: p["value"]
            for p in get_vehicle_properties()
            if p.get("property") == "in_list_view"
        }

    def test_license_plate_is_turned_on_and_odometer_off(self):
        setters = self._in_list_view_setters()
        self.assertEqual(setters.get("license_plate"), "1")
        self.assertEqual(setters.get("last_odometer"), "0")

    def test_the_setters_are_well_formed(self):
        for p in get_vehicle_properties():
            if p.get("property") != "in_list_view":
                continue
            self.assertEqual(p["doc_type"], "Vehicle")
            self.assertEqual(p["doctype_or_field"], "DocField")
            self.assertEqual(p["property_type"], "Check")

    def test_the_pinned_columns_show_the_plate_and_not_the_odometer(self):
        fieldnames = [c["fieldname"] for c in PRODUCTION_COLUMNS]
        self.assertIn("license_plate", fieldnames)
        self.assertNotIn("last_odometer", fieldnames)

    def test_the_pinned_columns_are_valid_vehicle_fields(self):
        meta = frappe.get_meta("Vehicle")
        for column in PRODUCTION_COLUMNS:
            fieldname = column["fieldname"]
            if fieldname == "name":
                continue
            self.assertTrue(
                meta.has_field(fieldname), msg=f"{fieldname} is not a Vehicle field"
            )

    def test_total_fields_is_an_allowed_option(self):
        options = frappe.get_meta("List View Settings").get_field("total_fields").options
        self.assertIn(TOTAL_FIELDS, [o for o in options.split("\n") if o])

    def test_the_pinned_columns_serialise_to_the_stored_shape(self):
        # The List View Settings `fields` column is a JSON string of the same shape
        # the desk writes, so a round trip must be lossless.
        self.assertEqual(json.loads(json.dumps(PRODUCTION_COLUMNS)), PRODUCTION_COLUMNS)
