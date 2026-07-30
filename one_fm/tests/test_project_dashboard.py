import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.project_dashboard import get_data


class TestProjectDashboardConnections(FrappeTestCase):
    """
    WI-001776: a Project Manager sees linked Contracts with a count under the Sales
    group, and can open the filtered list or raise a new Contract from there.
    """

    def setUp(self):
        self.data = get_data()
        self.sales = next(
            g for g in self.data["transactions"] if g["label"] == frappe._("Sales")
        )

    def test_contracts_is_listed_next_to_sales_order(self):
        items = self.sales["items"]
        self.assertIn("Contracts", items)
        self.assertEqual(items.index("Contracts"), items.index("Sales Order") + 1)

    def test_contracts_links_to_the_project_via_the_dashboard_fieldname(self):
        # The badge count, the pre-filtered list and the prefilled new-Contract form
        # all key off this field, so its absence would silently break all three.
        fieldname = self.data["fieldname"]
        self.assertEqual(fieldname, "project")
        meta = frappe.get_meta("Contracts")
        self.assertTrue(meta.has_field(fieldname))

    def test_the_contracts_project_field_points_at_project(self):
        df = frappe.get_meta("Contracts").get_field("project")
        self.assertEqual(df.fieldtype, "Link")
        self.assertEqual(df.options, "Project")

    def test_contracts_needs_no_special_link_handling(self):
        # Contracts is reached by its own `project` field, so it must not be declared
        # as an internal link or a non-standard fieldname.
        self.assertNotIn("Contracts", self.data.get("internal_links", {}))
        self.assertNotIn("Contracts", self.data.get("non_standard_fieldnames", {}))

    def test_every_listed_doctype_exists(self):
        for group in self.data["transactions"]:
            for doctype in group["items"]:
                self.assertTrue(
                    frappe.db.exists("DocType", doctype), msg=f"{doctype} does not exist"
                )
