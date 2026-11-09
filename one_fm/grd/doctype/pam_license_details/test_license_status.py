# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A licence is Active while it carries employees and Inactive when it carries none."""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.pam_license_details.test_pam_license_details_processa_scripts import rules

_rules = rules()
license_status = _rules["license_status"]
recount_license_total = _rules["recount_license_total"]

LICENSE = "ZZ-TEST-LICENSE-STATUS"


class TestTheRule(FrappeTestCase):
	def test_no_employees_is_inactive(self):
		self.assertEqual(license_status(0, ""), "Inactive")
		self.assertEqual(license_status("0", "Active"), "Inactive")

	def test_a_blank_or_missing_total_counts_as_zero(self):
		self.assertEqual(license_status("", "Active"), "Inactive")
		self.assertEqual(license_status(None, None), "Inactive")

	def test_employees_make_it_active(self):
		self.assertEqual(license_status(5, "Inactive"), "Active")
		self.assertEqual(license_status("1", ""), "Active")

	def test_suspended_is_never_overwritten(self):
		self.assertEqual(license_status(5, "Suspended"), "Suspended")
		self.assertEqual(license_status(0, "Suspended"), "Suspended")


class TestTheEmployeeRecount(FrappeTestCase):
	def _recount(self, count, current, exists=True):
		refresh = mock.Mock()
		with (
			mock.patch.object(frappe.db, "exists", return_value=exists),
			mock.patch.dict(_rules, {"count_license_employees": lambda name: count, "refresh_pam_files": refresh}),
			mock.patch.object(frappe.db, "get_value", return_value=current),
			mock.patch.object(frappe.db, "set_value") as set_value,
		):
			recount_license_total(LICENSE)
		return set_value, refresh

	def test_it_writes_both_fields_in_one_call(self):
		set_value, _refresh = self._recount(4, "Inactive")
		set_value.assert_called_once_with(
			"PAM License Details",
			LICENSE,
			{"total_number_of_employees": "4", "status": "Active"},
			update_modified=False,
		)

	def test_a_flip_is_pushed_to_the_pam_files_once(self):
		_set_value, refresh = self._recount(0, "Active")
		refresh.assert_called_once_with(LICENSE, "Inactive")

	def test_the_files_are_always_brought_in_line(self):
		# refresh_pam_files only rewrites rows whose status differs.
		_set_value, refresh = self._recount(4, "Active")
		refresh.assert_called_once_with(LICENSE, "Active")

	def test_suspended_is_not_changed(self):
		set_value, refresh = self._recount(0, "Suspended")
		self.assertEqual(set_value.call_args.args[2]["status"], "Suspended")
		refresh.assert_called_once_with(LICENSE, "Suspended")

	def test_a_missing_licence_writes_nothing(self):
		set_value, refresh = self._recount(4, "Active", exists=False)
		set_value.assert_not_called()
		refresh.assert_not_called()
