import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, add_days

class TestCreditLimit(FrappeTestCase):
    def setUp(self):
        # Create a test company if it doesn't exist
        self.company = "_Test Company Credit Limit"
        if not frappe.db.exists("Company", self.company):
            company_doc = frappe.get_doc({
                "doctype": "Company",
                "company_name": self.company,
                "default_currency": "USD",
                "country": "United States"
            })
            company_doc.insert()
        
        # Create a test customer
        self.customer_name = "_Test Credit Limit Customer"
        if not frappe.db.exists("Customer", self.customer_name):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.customer_name,
                "customer_type": "Individual",
                "customer_group": "All Customer Groups",
                "territory": "All Territories"
            })
            customer.insert()
        else:
            customer = frappe.get_doc("Customer", self.customer_name)
        
        # Set a small credit limit
        customer.credit_limits = []
        customer.append("credit_limits", {
            "company": self.company,
            "credit_limit": 100
        })
        customer.save()
        self.customer = customer

        # Create a test item
        self.item_code = "_Test Item Credit Limit"
        if not frappe.db.exists("Item", self.item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": self.item_code,
                "item_name": self.item_code,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 1
            }).insert()

    def test_credit_limit_validation(self):
        # Create a Sales Order that exceeds the credit limit
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": self.customer.name,
            "company": self.company,
            "transaction_date": nowdate(),
            "delivery_date": add_days(nowdate(), 1),
            "currency": "USD",
            "selling_price_list": "Standard Selling",
            "items": [
                {
                    "item_code": self.item_code,
                    "qty": 10,
                    "rate": 20, # Total 200, exceeds 100
                    "delivery_date": add_days(nowdate(), 1),
                    "uom": "Nos",
                    "conversion_factor": 1.0
                }
            ]
        })
        so.insert()
        
        # Submission should fail
        # We expect a ValidationError from our hook
        self.assertRaises(frappe.ValidationError, so.submit)

    def test_credit_limit_pass(self):
        # Create a Sales Order that is within the credit limit
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": self.customer.name,
            "company": self.company,
            "transaction_date": nowdate(),
            "delivery_date": add_days(nowdate(), 1),
            "currency": "USD",
            "selling_price_list": "Standard Selling",
            "items": [
                {
                    "item_code": self.item_code,
                    "qty": 2,
                    "rate": 20, # Total 40, within 100
                    "delivery_date": add_days(nowdate(), 1),
                    "uom": "Nos",
                    "conversion_factor": 1.0
                }
            ]
        })
        so.insert()
        
        # Submission should pass
        so.submit()
        self.assertEqual(so.docstatus, 1)

