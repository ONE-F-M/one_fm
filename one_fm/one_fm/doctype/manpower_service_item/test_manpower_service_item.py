# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

# WI-001710 AC: hidden when nationality is Kuwaiti. Translation, GP Ticket and Medical
# Test are named by the AC but do not exist on the doctype - shipped without them by
# decision, so they are not asserted here.
HIDDEN_FOR_KUWAITI = [
	"food_allowance",
	"laundry_allowance",
	"accommodation_allowance",
	"transportation_allowance",
	"uniform_cost",
	"air_ticket_allowance",
	"work_permit_fee",
	"medical_insurance_fee",
	"civil_id_fee",
]

NOT_KUWAITI = 'eval:doc.nationality != "Kuwaiti"'
IS_KUWAITI = 'eval:doc.nationality == "Kuwaiti"'


class TestManpowerServiceItemNationalityVisibility(FrappeTestCase):
	"""
	WI-001710: nationality-driven field visibility, read from the shipped doctype JSON so
	the assertions hold regardless of what the test site has migrated.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		path = frappe.get_app_path(
			"one_fm", "one_fm", "doctype", "manpower_service_item", "manpower_service_item.json"
		)
		cls.doctype_json = json.loads(frappe.read_file(path))
		cls.fields = {f["fieldname"]: f for f in cls.doctype_json["fields"]}

	def test_nationality_is_settable(self):
		"""
		The regression guard for why this story could not be demonstrated at all.

		nationality was Data + read_only with nothing in any controller or client script
		writing it, so the rules below always evaluated against an empty value and the
		form was permanently stuck on the non-Kuwaiti layout. If it goes back to read-only
		or loses its Select type, the whole feature silently dies again.
		"""
		nationality = self.fields["nationality"]
		self.assertEqual(nationality["fieldtype"], "Select")
		self.assertFalse(nationality.get("read_only"), "nationality must stay user-settable")

	def test_nationality_offers_the_three_values_the_rules_compare_against(self):
		# A Select carries its values in options; on a Data field the same list is inert.
		values = [v for v in self.fields["nationality"]["options"].split("\n")]
		self.assertIn("Kuwaiti", values)
		self.assertIn("Non-Kuwaiti", values)
		self.assertIn("Non-State", values)
		self.assertIn("", values, "blank option keeps nationality optional")

	def test_allowance_and_visa_fields_hide_for_kuwaiti(self):
		for fieldname in HIDDEN_FOR_KUWAITI:
			self.assertIn(fieldname, self.fields, msg=fieldname)
			self.assertEqual(self.fields[fieldname].get("depends_on"), NOT_KUWAITI, msg=fieldname)

	def test_pifss_shows_only_for_kuwaiti(self):
		# AC reads "hidden for Non-Kuwaiti and Non-State", i.e. every other option;
		# WI-001711 confirms it ("only when Nationality = Kuwaiti ... else PIFSS = 0").
		self.assertEqual(self.fields["pifss_rate"].get("depends_on"), IS_KUWAITI)

	def test_wcf_insurance_stays_visible_for_every_nationality(self):
		# WI-001711: "applies to every row regardless of Nationality".
		self.assertIsNone(self.fields["wcf_insurance_fee"].get("depends_on"))

	def test_no_other_field_was_caught_by_the_visibility_rules(self):
		ruled = {
			name
			for name, f in self.fields.items()
			if f.get("depends_on") in (NOT_KUWAITI, IS_KUWAITI)
		}
		self.assertEqual(ruled, set(HIDDEN_FOR_KUWAITI) | {"pifss_rate"})
