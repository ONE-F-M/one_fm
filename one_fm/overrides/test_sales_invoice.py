import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from one_fm.operations.doctype.contracts.contracts import calculate_item_values
from one_fm.overrides.purchase_order import calculate_margin
from one_fm.overrides.sales_invoice import SalesInvoiceOverride

NEGATIVE_MARGIN_WARNING = "Negative margin applied \u2014 selling price is below purchase cost."


class TestSalesInvoiceMargin(FrappeTestCase):
	"""Selling margin on refundable Sales Invoice rows.

	Documents are built in memory and never inserted, so no customer, item or contract
	fixtures are needed. The custom fields must exist (bench migrate) before running.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		cls.currency = frappe.get_cached_value("Company", cls.company, "default_currency")

	def make_invoice(self, rate=5, qty=10, margin_type=None, margin=0, refundable=1):
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"currency": self.currency,
				"conversion_rate": 1,
				"plc_conversion_rate": 1,
				"items": [
					{
						"doctype": "Sales Invoice Item",
						"item_code": "_Test Margin Item",
						"qty": qty,
						"rate": rate,
						"price_list_rate": rate,
						"custom_refundable": refundable,
						"custom_margin_type": margin_type or "",
						"custom_margin_rate_or_amount": margin,
					}
				],
			}
		)
		return doc

	def calculate(self, doc):
		doc.calculate_taxes_and_totals()
		return doc.items[0]

	def warnings(self):
		messages = []
		for entry in frappe.local.message_log:
			if isinstance(entry, str):
				entry = json.loads(entry)
			messages.append(entry)
		return messages

	# AC1
	def test_percentage_margin_line_amount(self):
		item = self.calculate(self.make_invoice(margin_type="Percentage", margin=10))
		self.assertEqual(flt(item.amount, 3), 55.000)
		self.assertEqual(flt(item.net_amount, 3), 55.000)
		# base cost and markup are held separately
		self.assertEqual(flt(item.custom_base_amount, 3), 50.000)
		self.assertEqual(item.custom_margin_display, "10%")

	# AC2
	def test_amount_margin_line_amount(self):
		item = self.calculate(self.make_invoice(margin_type="Amount", margin=2))
		self.assertEqual(flt(item.amount, 3), 70.000)
		self.assertEqual(flt(item.custom_base_amount, 3), 50.000)
		self.assertTrue(item.custom_margin_display.startswith("2.000 "))

	# AC3
	def test_base_margin_and_net_amount_are_distinct_fields(self):
		meta = frappe.get_meta("Sales Invoice Item")
		for fieldname in (
			"custom_margin_type",
			"custom_margin_rate_or_amount",
			"custom_base_amount",
			"custom_margin_display",
			"amount",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)

		pct = self.calculate(self.make_invoice(margin_type="Percentage", margin=10))
		self.assertEqual(
			(flt(pct.custom_base_amount, 3), pct.custom_margin_display, flt(pct.net_amount, 3)),
			(50.000, "10%", 55.000),
		)

	# AC4
	def test_zero_margin_keeps_base_cost(self):
		pct = self.calculate(self.make_invoice(margin_type="Percentage", margin=0))
		self.assertEqual(flt(pct.amount, 3), 50.000)
		self.assertEqual(pct.custom_margin_display, "0%")

		amt = self.calculate(self.make_invoice(margin_type="Amount", margin=0))
		self.assertEqual(flt(amt.amount, 3), 50.000)
		self.assertTrue(amt.custom_margin_display.startswith("0.000 "))

	def test_refundable_row_without_margin_type_is_unchanged_cost(self):
		item = self.calculate(self.make_invoice())
		self.assertEqual(flt(item.amount, 3), 50.000)

	# AC5: a real negative margin, not a discount, plus a non-blocking warning
	def test_negative_margin_is_a_real_negative_margin(self):
		item = self.calculate(self.make_invoice(margin_type="Percentage", margin=-10))
		self.assertEqual(flt(item.rate, 3), 4.500)
		self.assertEqual(flt(item.amount, 3), 45.000)
		self.assertEqual(item.custom_margin_display, "-10%")
		# not converted to a discount
		self.assertEqual(flt(item.discount_amount, 3), 0)
		self.assertEqual(flt(item.discount_percentage, 3), 0)

	def test_negative_margin_raises_orange_warning_without_blocking(self):
		doc = self.make_invoice(margin_type="Percentage", margin=-10)
		frappe.clear_messages()
		SalesInvoiceOverride.validate_selling_margin(doc)  # must not raise
		matching = [m for m in self.warnings() if m.get("message") == NEGATIVE_MARGIN_WARNING]
		self.assertEqual(len(matching), 1)
		self.assertEqual(matching[0].get("indicator"), "orange")

	def test_positive_margin_has_no_warning(self):
		doc = self.make_invoice(margin_type="Percentage", margin=10)
		frappe.clear_messages()
		SalesInvoiceOverride.validate_selling_margin(doc)
		self.assertFalse([m for m in self.warnings() if m.get("message") == NEGATIVE_MARGIN_WARNING])

	def test_margin_that_zeroes_the_price_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			SalesInvoiceOverride.validate_selling_margin(self.make_invoice(margin_type="Percentage", margin=-100))
		with self.assertRaises(frappe.ValidationError):
			SalesInvoiceOverride.validate_selling_margin(self.make_invoice(margin_type="Amount", margin=-5))

	def test_margin_without_type_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			SalesInvoiceOverride.validate_selling_margin(self.make_invoice(margin=10))

	def test_recalculation_does_not_compound_margin(self):
		doc = self.make_invoice(margin_type="Percentage", margin=10)
		self.calculate(doc)
		item = self.calculate(doc)
		self.assertEqual(flt(item.amount, 3), 55.000)

	def test_non_refundable_row_ignores_margin_fields(self):
		# Amount recalculation is refundable-only: other rows keep the amount they arrived with.
		doc = self.make_invoice(margin_type="Percentage", margin=10, refundable=0)
		doc.items[0].amount = 50
		item = self.calculate(doc)
		self.assertEqual(flt(item.amount, 3), 50.000)
		self.assertFalse(item.custom_margin_display)

	def test_negative_margin_ignores_discount_written_by_browser(self):
		# ERPNext's rate handler turns rate < price_list_rate into a discount.
		doc = self.make_invoice(margin_type="Percentage", margin=-10)
		doc.items[0].rate = 4.5
		doc.items[0].discount_percentage = 10
		doc.items[0].discount_amount = 0.5
		item = self.calculate(doc)
		self.assertEqual(flt(item.amount, 3), 45.000)

	def test_recalculation_without_price_list_rate_does_not_compound(self):
		doc = self.make_invoice(margin_type="Percentage", margin=10)
		doc.items[0].price_list_rate = 0
		self.calculate(doc)
		item = self.calculate(doc)
		self.assertEqual(flt(item.price_list_rate, 3), 5.000)
		self.assertEqual(flt(item.amount, 3), 55.000)

	def test_refundable_purchase_row_keeps_rate(self):
		doc = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"conversion_rate": 1,
				"items": [
					{
						"doctype": "Purchase Invoice Item",
						"qty": 2,
						"price_list_rate": 10,
						"discount_percentage": 10,
						"discount_amount": 1,
						"rate": 9,
						"margin_type": "Amount",
						"margin_rate_or_amount": 1,
						"custom_refundable": 1,
					}
				],
			}
		)
		calc = frappe._dict(doc=doc, discount_amount_applied=False)
		calc.calculate_margin = lambda item: calculate_margin(calc, item)
		calc._set_in_company_currency = lambda item, fields: None
		calculate_item_values(calc)
		calculate_item_values(calc)
		self.assertEqual(flt(doc.items[0].rate, 3), 9.000)
