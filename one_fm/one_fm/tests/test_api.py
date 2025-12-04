import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.one_fm.api.api import get_monthly_sales_summary


class TestSalesInvoiceAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_test_item()
		cls.customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert(ignore_permissions=True)

		cls.create_sales_invoice(2, 2023, 100)
		cls.create_sales_invoice(5, 2023, 200)
		cls.create_sales_invoice(5, 2023, 50)
		cls.create_sales_invoice(1, 2024, 300)

	@classmethod
	def create_sales_invoice(cls, month, year, amount):
		frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": cls.customer.name,
				"posting_date": f"{year}-{month:02d}-01",
				"due_date": nowdate(),
				"items": [
					{
						"item_code": "Test Item",
						"qty": 1,
						"rate": amount,
					}
				],
			}
		).insert(ignore_permissions=True).submit()

	def test_get_monthly_sales_summary(self):
		frappe.set_user("Administrator")

		summary_2023 = get_monthly_sales_summary(self.customer.name, 2023)
		self.assertEqual(len(summary_2023), 12)
		self.assertEqual(summary_2023[1]["total"], 100)
		self.assertEqual(summary_2023[4]["total"], 250)
		self.assertEqual(summary_2023[0]["total"], 0)

		summary_2024 = get_monthly_sales_summary(self.customer.name, 2024)
		self.assertEqual(len(summary_2024), 12)
		self.assertEqual(summary_2024[0]["total"], 300)
		self.assertEqual(summary_2024[1]["total"], 0)

		summary_2025 = get_monthly_sales_summary(self.customer.name, 2025)
		self.assertEqual(len(summary_2025), 12)
		self.assertTrue(all(s["total"] == 0 for s in summary_2025))

	def test_permission(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_monthly_sales_summary(self.customer.name, 2023)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


def create_test_item():
	if not frappe.db.exists("Item", "Test Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Test Item",
				"item_group": "All Item Groups",
			}
