import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.one_fm.api import get_customer_sales_invoice_summary


class TestCustomerSalesInvoiceAPI(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = create_customer()
        create_sales_invoices(cls.customer)

    def test_get_customer_sales_invoice_summary_success(self):
        frappe.set_user("test@example.com")
        summary = get_customer_sales_invoice_summary(self.customer.name)
        self.assertEqual(summary["total_invoices"], 2)
        self.assertEqual(summary["total_invoiced_amount"], 300)
        self.assertEqual(summary["total_outstanding_amount"], 150)

    def test_get_customer_sales_invoice_summary_not_found(self):
        frappe.set_user("test@example.com")
        with self.assertRaises(frappe.DoesNotExistError):
            get_customer_sales_invoice_summary("Non Existent Customer")

    def test_get_customer_sales_invoice_summary_permission_error(self):
        frappe.set_user("test1@example.com")
        with self.assertRaises(frappe.PermissionError):
            get_customer_sales_invoice_summary(self.customer.name)


def create_customer():
    customer = frappe.db.exists("Customer", "Test Customer")
    if not customer:
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": "Test Customer",
                "customer_group": "All Customer Groups",
                "territory": "All Territories",
            }
        ).insert()
    return customer


def create_sales_invoices(customer):
    inv1 = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": customer.name,
            "posting_date": nowdate(),
            "due_date": nowdate(),
            "items": [{"item_code": "Test Item", "qty": 1, "rate": 100}],
            "outstanding_amount": 50,
        }
    ).insert()
    inv1.submit()

    inv2 = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": customer.name,
            "posting_date": nowdate(),
            "due_date": nowdate(),
            "items": [{"item_code": "Test Item", "qty": 1, "rate": 200}],
            "outstanding_amount": 100,
        }
    ).insert()
