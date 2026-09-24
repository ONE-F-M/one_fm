"""WI-002884: make the Customer's Full Name In Arabic mandatory on sites that already have it.

The fixture in one_fm/custom/custom_field/customer.py is only applied by `after_install`
and by `add_update_custom_field`, a patch that ran on 2026-01-04 and will not run again.
On every existing site the Custom Field row is already there, so editing the fixture alone
changes nothing at all - the flag would only ever reach a site installed from scratch.

Written directly onto the row for the same reason WI-002823's does: create_custom_fields
applies the keys it is handed, but nothing hands them over after install.

## What this does to the 215 Customers on production

211 of them have no Arabic name. Mandatory bites on save, not retrospectively, so nothing
breaks today - but the next person to edit one of those 211 has to supply the Arabic name
before they can save. That is what the story asks for, and it is the point: the Proof of
Work letter (WI-002722) prints the Arabic name and falls back to English until it is
there. No name is invented here; an Arabic company name is the business's to supply.
"""

import frappe

FIELD = "Customer-customer_name_in_arabic"


def execute():
	if not frappe.db.exists("Custom Field", FIELD):
		# A site that has not had the fixture applied yet. after_install will create it
		# mandatory, so there is nothing to correct.
		return

	frappe.db.set_value("Custom Field", FIELD, "reqd", 1)
	frappe.clear_cache(doctype="Customer")

	verify()


def verify():
	if not frappe.get_meta("Customer").get_field("customer_name_in_arabic").reqd:
		frappe.throw(
			"WI-002884: Customer.customer_name_in_arabic is still optional, so the Proof "
			"of Work letter goes on falling back to the English name."
		)
