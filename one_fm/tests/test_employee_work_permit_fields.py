# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002618: retire the two work-permit fields on Employee, and say what the visa date means.

Three changes that only make sense together:

* ``one_fm_work_permit`` - a HIDDEN Data field holding a Work Permit's name - goes, and the
  three places that read it now read ``work_permit``, the Link field sitting right beside it
  that was always the proper one. Both columns are empty on current data, so this swap moves
  no values; it just stops the code reading the wrong one of two identically-labelled fields.
* ``pam_type`` goes, along with the controller and form handlers that cleared
  ``residency_expiry_date`` for Kuwaitis - and the depends_on that hid it, which is the part
  that would otherwise break silently.
* ``one_fm_date_of_issuance_of_visa`` is relabelled Date of Visa Expiry. The fieldname stays;
  renaming it would break the Work Permit's fetch_from for no gain.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.patches.v15_0.remove_employee_work_permit_fields import (
	RESIDENCY_EXPIRY_DEPENDS_ON,
	REMOVED,
)

REMOVED_FIELDS = ("one_fm_work_permit", "pam_type")


class TestTheFieldsAreGone(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.fields = {f["fieldname"]: f for f in get_employee_custom_fields()["Employee"]}

	def test_neither_field_is_defined_any_more(self):
		for fieldname in REMOVED_FIELDS:
			self.assertNotIn(fieldname, self.fields)

	def test_the_patch_removes_exactly_those_two(self):
		self.assertEqual(
			sorted(f["fieldname"] for f in REMOVED["Employee"]), sorted(REMOVED_FIELDS)
		)

	def test_nothing_is_left_pointing_at_a_field_that_no_longer_exists(self):
		# insert_after naming a removed field is the quiet way a whole section ends up in
		# the wrong place: Frappe appends the orphan at the end rather than complaining.
		for fieldname, field in self.fields.items():
			self.assertNotIn(field.get("insert_after"), REMOVED_FIELDS, msg=fieldname)

	def test_the_field_order_no_longer_lists_them(self):
		from one_fm.custom.property_setter.employee import get_employee_properties

		order = [p for p in get_employee_properties() if p.get("property") == "field_order"]
		self.assertTrue(order, "Employee has no field_order property setter any more")
		for setter in order:
			for fieldname in REMOVED_FIELDS:
				self.assertNotIn(f'"{fieldname}"', setter["value"], msg=fieldname)

	def test_the_link_field_survives_and_is_still_a_link(self):
		# The whole point of dropping the Data one is that this is the real field.
		self.assertEqual(self.fields["work_permit"]["fieldtype"], "Link")
		self.assertEqual(self.fields["work_permit"]["options"], "Work Permit")


class TestWhatUsedToReadThem(FrappeTestCase):
	def test_the_work_permit_lookups_read_the_link_field(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "work_permit", "work_permit.py")
		)
		self.assertNotIn("employee.one_fm_work_permit", source)
		self.assertEqual(source.count("frappe.get_doc('Work Permit', employee.work_permit)"), 3)

	def test_the_controller_no_longer_clears_residency_expiry(self):
		source = frappe.read_file(frappe.get_app_path("one_fm", "overrides", "employee.py"))
		self.assertNotIn("pam_type", source)

	def test_the_form_no_longer_clears_residency_expiry(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "public", "js", "doctype_js", "employee.js")
		)
		self.assertNotIn("pam_type", source)

	def test_the_rest_of_the_employee_controller_is_untouched(self):
		# The removed block sat in the middle of validate(); everything under it has to
		# still be called.
		source = frappe.read_file(frappe.get_app_path("one_fm", "overrides", "employee.py"))
		for call in (
			"self.set_employee_name()",
			"self.set_employee_id_based_on_residency()",
			"self.validate_reliever()",
			"self.validate_status()",
			"self.toggle_auto_attendance()",
		):
			self.assertIn(call, source, msg=call)


class TestTheResidencyExpiryCondition(FrappeTestCase):
	"""The part that would have broken without anyone noticing.

	residency_expiry_date was hidden by

	    eval:doc.under_company_residency==1 && doc.pam_type != "Kuwaiti"

	With pam_type gone, `undefined != "Kuwaiti"` is true, so the field would start showing
	for the employees it was written to hide it from - 149 of them on current data.
	"""

	def test_the_condition_no_longer_names_the_removed_field(self):
		self.assertNotIn("pam_type", RESIDENCY_EXPIRY_DEPENDS_ON)

	def test_it_still_depends_on_being_under_company_residency(self):
		self.assertEqual(RESIDENCY_EXPIRY_DEPENDS_ON, "eval:doc.under_company_residency==1")


class TestTheVisaDate(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.field = {
			f["fieldname"]: f for f in get_employee_custom_fields()["Employee"]
		}["one_fm_date_of_issuance_of_visa"]

	def test_it_is_labelled_as_the_expiry(self):
		self.assertEqual(self.field["label"], "Date of Visa Expiry")

	def test_the_fieldname_is_deliberately_unchanged(self):
		# Renaming it would break work_permit.json's fetch_from and everything else that
		# names it, to no end - what changed is the meaning, not the column.
		self.assertEqual(self.field["fieldname"], "one_fm_date_of_issuance_of_visa")

	def test_it_is_still_a_date_in_the_same_place(self):
		self.assertEqual(self.field["fieldtype"], "Date")
		self.assertEqual(self.field["insert_after"], "one_fm_visa_reference_number")

	def test_the_work_permit_still_fetches_it(self):
		# Out of this story's scope, but it means the Work Permit's own field now receives
		# an expiry date. Flagged on the PR rather than changed here.
		permit = frappe.get_meta("Work Permit").get_field("date_of_issuance_of_visa")
		if permit:
			self.assertEqual(permit.fetch_from, "employee.one_fm_date_of_issuance_of_visa")


class TestThePatchIsWiredUp(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.remove_employee_work_permit_fields", patches)

	def test_removal_does_not_drop_the_stored_values(self):
		# delete_custom_fields deletes the Custom Field ROWS, not the Employee columns, so
		# pam_type's 2,958 values survive and this is reversible. Worth pinning: switching
		# it to frappe.delete_doc would silently start dropping columns.
		source = frappe.read_file(frappe.get_app_path("one_fm", "setup", "setup.py"))
		body = source.split("def delete_custom_fields", 1)[1].split("\ndef ", 1)[0]
		self.assertIn('frappe.db.delete(', body)
		self.assertNotIn("delete_doc", body)
