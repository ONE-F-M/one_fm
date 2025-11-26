import frappe,json
from frappe.tests.utils import FrappeTestCase
import unittest


class TestPurchaseOrder_(FrappeTestCase):
    def test_validate_custom_fields(self):
        doctype_meta = frappe.get_meta("Purchase Order")
        field_order = json.loads(doctype_meta.field_order)
        self.assertIn('custom_place_of_delivery', field_order)
        self.assertIn('custom_terms_of_shipment', field_order)

    def test_request_for_purchase_validation(self):
        po = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": "_Test Supplier",
            "company": "_Test Company",
            "request_for_material": "_Test Request for Material",
            "items": [
                {
                    "item_code": "_Test Item",
                    "qty": 1
                }
            ]
        })
        self.assertRaises(frappe.ValidationError, po.insert)
        