# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002031: master fee rows in HR Settings and how a Preparation row fetches them."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	COST_COMPONENT_FIELDS,
	YEAR_SCOPED_ACTIONS,
	category_for_action,
	get_grd_renewal_extension_cost,
)
from one_fm.grd.utils import set_renewal_extension_cost_totals

GOVERNMENT = "Overseas (Government)"
PRIVATE = "Overseas"


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


def _master_rows(rows):
	"""Replace the HR Settings costing table with the given rows and save."""
	settings = frappe.get_doc("HR Settings")
	settings.set("renewal_extension_cost", [])
	for row in rows:
		settings.append("renewal_extension_cost", row)
	settings.flags.ignore_permissions = True
	settings.save()
	return settings


class TestActionFeeMaster(FrappeTestCase):
	def test_the_hr_settings_totals_hook_is_registered(self):
		self.assertIn(
			"one_fm.grd.utils.set_renewal_extension_cost_totals",
			frappe.get_hooks("doc_events").get("HR Settings", {}).get("validate", []),
		)

	def test_a_master_row_total_is_the_sum_of_its_components(self):
		doc = frappe._dict(
			renewal_extension_cost=[
				frappe._dict(
					work_permit_amount=210,
					medical_insurance_amount=50,
					residency_stamp_amount=10,
					civil_id_amount=5,
					total_amount=0,
				)
			]
		)
		# _dict has no .get_ semantics for child rows, so mimic what a Document gives us.
		doc.get = lambda field, default=None: doc.__dict__.get(field, default)

		set_renewal_extension_cost_totals(doc)

		self.assertEqual(doc.renewal_extension_cost[0].total_amount, 275)

	def test_a_zero_component_contributes_nothing_to_the_master_total(self):
		row = frappe._dict(
			work_permit_amount=210,
			medical_insurance_amount=0,
			residency_stamp_amount=0,
			civil_id_amount=0,
			total_amount=999,
		)
		doc = frappe._dict(renewal_extension_cost=[row])
		doc.get = lambda field, default=None: doc.__dict__.get(field, default)

		set_renewal_extension_cost_totals(doc)

		self.assertEqual(row.total_amount, 210)

	def test_saving_hr_settings_derives_the_row_total(self):
		settings = _master_rows(
			[
				{
					"renewal_or_extend": GOVERNMENT,
					"work_permit_amount": 60,
					"medical_insurance_amount": 0,
					"residency_stamp_amount": 0,
					"civil_id_amount": 0,
					"total_amount": 12345,  # a stale total the read-only field was holding
				}
			]
		)
		self.assertEqual(settings.renewal_extension_cost[0].total_amount, 60)

	def test_each_action_fetches_its_own_work_permit_rate(self):
		_master_rows(
			[
				{"renewal_or_extend": PRIVATE, "work_permit_amount": 210},
				{"renewal_or_extend": GOVERNMENT, "work_permit_amount": 60},
			]
		)

		self.assertEqual(get_grd_renewal_extension_cost(PRIVATE)["work_permit_amount"], 210)
		self.assertEqual(get_grd_renewal_extension_cost(GOVERNMENT)["work_permit_amount"], 60)

	def test_a_renewal_is_scoped_by_the_number_of_years(self):
		# The old lookup filtered on the years only when the Action was exactly "Renewal",
		# a value the field has not offered for years, so this used to return whichever row
		# the database handed back first.
		action = YEAR_SCOPED_ACTIONS[1]
		_master_rows(
			[
				{"renewal_or_extend": action, "no_of_years": "1 Year", "work_permit_amount": 100},
				{"renewal_or_extend": action, "no_of_years": "2 Years", "work_permit_amount": 200},
				{"renewal_or_extend": action, "no_of_years": "3 Years", "work_permit_amount": 300},
			]
		)

		self.assertEqual(get_grd_renewal_extension_cost(action, "2 Years")["work_permit_amount"], 200)
		self.assertEqual(get_grd_renewal_extension_cost(action, "3 Years")["work_permit_amount"], 300)

	def test_a_renewal_without_a_year_fetches_nothing(self):
		self.assertFalse(get_grd_renewal_extension_cost(YEAR_SCOPED_ACTIONS[0]))

	def test_a_non_renewal_action_ignores_a_stale_year(self):
		# The field is hidden but not cleared when the Action changes, so an Extend row can
		# still carry "1 Year". Scoping by it would find nothing and return no fees.
		_master_rows([{"renewal_or_extend": "Extend 1 month", "work_permit_amount": 25}])

		self.assertEqual(
			get_grd_renewal_extension_cost("Extend 1 month", "1 Year")["work_permit_amount"], 25
		)

	def test_an_unconfigured_action_returns_nothing_rather_than_a_wrong_row(self):
		_master_rows([{"renewal_or_extend": PRIVATE, "work_permit_amount": 210}])

		self.assertFalse(get_grd_renewal_extension_cost(GOVERNMENT))

	def test_the_action_is_not_interpolated_into_the_query(self):
		# The Action arrives from the browser through a whitelisted method. Under the old
		# string-formatted SQL this closed the quote and ran on.
		self.assertFalse(get_grd_renewal_extension_cost("' OR 1=1 -- "))

	def test_a_preparation_row_total_is_derived_from_its_components(self):
		preparation = frappe.get_doc(
			{
				"doctype": "Preparation",
				"category": category_for_action(GOVERNMENT),
				"posting_date": nowdate(),
				"preparation_record": [
					{
						"employee": _an_active_employee(),
						"renewal_or_extend": GOVERNMENT,
						"work_permit_amount": 60,
						"medical_insurance_amount": 0,
						"residency_stamp_amount": 10,
						"civil_id_amount": 5,
						"total_amount": 9999,  # not what the components add up to
					}
				],
			}
		)
		preparation.flags.ignore_permissions = True
		preparation.insert()

		self.assertEqual(preparation.preparation_record[0].total_amount, 75)
		self.assertEqual(preparation.total_payment, 75)

	def test_the_component_list_matches_the_master_and_the_row(self):
		for doctype in ("GRD Renewal Extension Cost", "Preparation Record"):
			meta = frappe.get_meta(doctype)
			for field in COST_COMPONENT_FIELDS:
				self.assertTrue(meta.get_field(field), f"{doctype} has no {field}")
