# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001834: the Shift Preview an approver reads, and what gets created from it."""

import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from one_fm.overrides.shift_request import build_shift_preview, shift_type_on

# 2027-01-01 is a Friday; the week after it contains exactly one more Friday.
A_FRIDAY = "2027-01-01"
A_MONDAY = "2027-01-04"
A_TUESDAY = "2027-01-05"


def _an_operations_shift():
	name = frappe.db.get_value(
		"Operations Shift",
		{"status": "Active", "shift_type": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active Operations Shift on this site to test against")
	return name


class TestShiftRequestPreview(FrappeTestCase):
	def setUp(self):
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

		default_hours = frappe.db.get_value(
			"Shift Type", self.default_type, ["start_time", "end_time"], as_dict=True
		)
		self.override_type = frappe.db.get_value(
			"Shift Type",
			{"name": ["!=", self.default_type], "start_time": ["!=", default_hours.start_time]},
			"name",
			order_by="name asc",
		)
		if not self.override_type:
			self.skipTest("No second Shift Type on this site to override with")

		self._set_override(True)

	def tearDown(self):
		self._set_override(False)

	def _set_override(self, on):
		"""Configure the post without saving it, which would enqueue the WI-001831 re-stamp."""
		frappe.db.set_value(
			"Operations Shift", self.shift_name, "shift_timing_override_required", int(on),
			update_modified=False,
		)
		frappe.db.delete(
			"Operations Shift Timing",
			{"parent": self.shift_name, "parenttype": "Operations Shift"},
		)
		if on:
			row = frappe.get_doc({
				"doctype": "Operations Shift Timing",
				"parent": self.shift_name,
				"parenttype": "Operations Shift",
				"parentfield": "operations_shift_timing",
				"idx": 1,
				"day_of_week": "Friday",
				"shift_type": self.override_type,
			})
			row.db_insert()
		frappe.clear_document_cache("Operations Shift", self.shift_name)

	def _request(self, from_date, to_date):
		"""An in-memory Shift Request. build_shift_preview reads only these four fields."""
		return frappe.get_doc({
			"doctype": "Shift Request",
			"operations_shift": self.shift_name,
			"shift_type": self.default_type,
			"from_date": from_date,
			"to_date": to_date,
		})

	# ------------------------------------------------------------------- AC 1 & 3

	def test_a_range_containing_an_override_day_is_previewed(self):
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)

		self.assertEqual(len(request.custom_shift_preview), 5)

	def test_every_previewed_row_carries_date_day_and_shift_type(self):
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)

		for row in request.custom_shift_preview:
			self.assertTrue(row.date)
			self.assertTrue(row.day)
			self.assertTrue(row.shift_type)

	def test_the_override_day_shows_the_override_and_the_rest_the_default(self):
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)

		by_day = {row.day: row.shift_type for row in request.custom_shift_preview}
		self.assertEqual(by_day["Friday"], self.override_type)
		self.assertEqual(by_day["Monday"], self.default_type)
		self.assertEqual(by_day["Tuesday"], self.default_type)

	def test_the_day_column_matches_the_date(self):
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)

		for row in request.custom_shift_preview:
			self.assertEqual(row.day, frappe.utils.getdate(row.date).strftime("%A"))

	def test_a_default_only_range_stays_empty(self):
		# AC3: the section is hidden on depends_on, so an empty table is a hidden table.
		request = self._request(A_MONDAY, A_TUESDAY)

		build_shift_preview(request)

		self.assertEqual(len(request.custom_shift_preview), 0)

	def test_a_post_with_no_override_required_stays_empty(self):
		self._set_override(False)
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)

		self.assertEqual(len(request.custom_shift_preview), 0)

	def test_a_single_override_day_is_previewed(self):
		request = self._request(A_FRIDAY, A_FRIDAY)

		build_shift_preview(request)

		self.assertEqual(len(request.custom_shift_preview), 1)
		self.assertEqual(request.custom_shift_preview[0].shift_type, self.override_type)

	def test_rebuilding_does_not_stack_rows(self):
		request = self._request(A_FRIDAY, A_TUESDAY)

		build_shift_preview(request)
		build_shift_preview(request)

		self.assertEqual(len(request.custom_shift_preview), 5)

	def test_an_incomplete_request_is_left_alone(self):
		for kwargs in (
			{"from_date": None, "to_date": A_TUESDAY},
			{"from_date": A_FRIDAY, "to_date": None},
		):
			request = self._request(**kwargs)
			request.operations_shift = self.shift_name
			build_shift_preview(request)
			self.assertEqual(len(request.custom_shift_preview), 0)

	def test_the_grid_is_read_only(self):
		field = frappe.get_meta("Shift Request").get_field("custom_shift_preview")
		self.assertTrue(field.read_only)
		self.assertEqual(field.options, "Shift Preview")

	def test_both_new_fields_hide_on_an_empty_preview(self):
		meta = frappe.get_meta("Shift Request")
		for fieldname in ("custom_section_break_z4s37", "custom_shift_preview"):
			self.assertEqual(
				meta.get_field(fieldname).depends_on,
				"eval:doc.custom_shift_preview && doc.custom_shift_preview.length",
			)

	# ----------------------------------------------------------------------- AC 2

	def test_what_gets_created_reads_the_previewed_date(self):
		request = self._request(A_FRIDAY, A_TUESDAY)
		build_shift_preview(request)

		self.assertEqual(shift_type_on(request, A_FRIDAY), self.override_type)
		self.assertEqual(shift_type_on(request, A_MONDAY), self.default_type)

	def test_an_unpreviewed_request_falls_back_to_its_own_shift_type(self):
		# A default-only range behaves exactly as it did before this story.
		request = self._request(A_MONDAY, A_TUESDAY)
		build_shift_preview(request)

		self.assertEqual(shift_type_on(request, A_MONDAY), self.default_type)

	def test_a_date_outside_the_preview_falls_back(self):
		request = self._request(A_FRIDAY, A_FRIDAY)
		build_shift_preview(request)

		self.assertEqual(shift_type_on(request, add_days(A_FRIDAY, 40)), self.default_type)

	def test_a_plain_dict_request_falls_back_without_error(self):
		# One branch builds a frappe._dict rather than a document to hand on.
		request = frappe._dict({"shift_type": self.default_type})

		self.assertEqual(shift_type_on(request, A_FRIDAY), self.default_type)


class TestThePatchIsActuallyRegistered(FrappeTestCase):
	"""The regression that took Shift Request down on staging.

	The patch that creates `custom_shift_preview` was listed only in a stray
	`patches.txt` at the repo root, which Frappe never reads - it reads
	`one_fm/patches.txt`. So the patch never ran, the Custom Field was never created, and
	`doc.append("custom_shift_preview", ...)` raised AttributeError on every save of a
	request whose range covers an override day.

	The field assertions above pass on a site where the patch has been run by hand, so they
	could not see this. This one checks the registration itself.
	"""

	def setUp(self):
		self.patches = pathlib.Path(frappe.get_app_path("one_fm", "patches.txt")).read_text()

	def test_the_shift_preview_patch_is_listed(self):
		self.assertIn("one_fm.patches.v15_0.add_shift_request_shift_preview", self.patches)

	def test_it_runs_after_the_model_sync(self):
		# The Table field's options point at the Shift Preview child DocType, which only
		# exists once the model sync has run. Registered pre_model_sync, create_custom_fields
		# fails on the link and leaves the section break behind without the grid - which is
		# exactly the half-created state staging was found in.
		post = self.patches.split("[post_model_sync]", 1)
		self.assertEqual(len(post), 2, "patches.txt has no [post_model_sync] section")
		self.assertIn("one_fm.patches.v15_0.add_shift_request_shift_preview", post[1])

	def test_there_is_no_stray_patches_file_at_the_repo_root(self):
		# It has been re-introduced three times this sprint. Frappe ignores it, so anything
		# landing there is silently never applied.
		root = pathlib.Path(frappe.get_app_path("one_fm")).parent / "patches.txt"

		self.assertFalse(root.exists(), f"{root} is not read by Frappe - move its entries into one_fm/patches.txt")

	def test_the_child_doctype_the_grid_points_at_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Shift Preview"))
		self.assertTrue(frappe.get_meta("Shift Preview").istable)
