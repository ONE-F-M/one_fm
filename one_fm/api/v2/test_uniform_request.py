# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002301: the mobile Uniform Request endpoint, and the rules around it.

An employee reports a damaged uniform item - what it is, what size, a photo. Everything
else about the Request for Material it becomes, they should not have to type.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v2.uniform_request import (
	INDIVIDUAL,
	PENDING_APPROVAL,
	UNIFORM_QTY,
	_missing_details,
	_photo_of,
)

SIZE = "XL"
PHOTO = "/files/wi002301-damaged.jpg"


class TestTheFieldsExist(FrappeTestCase):
	def test_the_line_carries_a_size(self):
		field = frappe.get_meta("Request for Material Item").get_field("size")

		self.assertIsNotNone(field, "Request for Material Item has no Size field")
		self.assertEqual(field.fieldtype, "Data")

	def test_size_is_shown_only_on_an_individual_request(self):
		"""Scoped so the other request types are untouched."""
		field = frappe.get_meta("Request for Material Item").get_field("size")

		self.assertIn('parent.type == "Individual"', field.depends_on)

	def test_size_is_required_on_a_uniform_line(self):
		field = frappe.get_meta("Request for Material Item").get_field("size")

		self.assertIn("doc.is_uniform_request", field.mandatory_depends_on)

	def test_the_line_already_carries_the_uniform_flag_and_a_photo(self):
		meta = frappe.get_meta("Request for Material Item")

		self.assertIsNotNone(meta.get_field("is_uniform_request"))
		self.assertEqual(meta.get_field("attach_photo").fieldtype, "Attach Image")


class TestRequiredDateStaysMandatoryElsewhere(FrappeTestCase):
	"""It stopped being unconditionally required so a uniform request can be started
	without one. Every other request type has to keep the rule it had."""

	def test_it_is_no_longer_unconditionally_required(self):
		self.assertFalse(frappe.get_meta("Request for Material").get_field("schedule_date").reqd)

	def test_the_form_still_demands_it_for_other_types(self):
		rule = frappe.get_meta("Request for Material").get_field("schedule_date").mandatory_depends_on

		self.assertIn('doc.type != "Individual"', rule)

	def test_the_server_still_demands_it_for_other_types(self):
		"""mandatory_depends_on is a form rule; the server only ever checked reqd."""
		request = frappe.new_doc("Request for Material")
		request.type = "Stock"
		request.schedule_date = None

		with self.assertRaises(frappe.ValidationError) as raised:
			request.validate_uniform_request_details()

		self.assertIn("Required Date", str(raised.exception))

	def test_an_individual_request_may_start_without_one(self):
		request = frappe.new_doc("Request for Material")
		request.type = INDIVIDUAL
		request.schedule_date = None

		request.validate_uniform_request_details()


class TestWhatTheEmployeeMustGive(FrappeTestCase):
	"""Scenario 4, enforced server-side as well as on the form."""

	def _row(self, **overrides):
		row = {"item_code": "ITEM", "size": SIZE, "attach_photo": PHOTO}
		row.update(overrides)
		return row

	def test_a_complete_row_passes(self):
		self.assertEqual(_missing_details([self._row()]), "")

	def test_a_row_with_no_size_is_named(self):
		message = _missing_details([self._row(size=None)])

		self.assertIn("Row 1", message)
		self.assertIn("size", message.lower())

	def test_a_row_with_no_photo_is_named(self):
		message = _missing_details([self._row(attach_photo=None)])

		self.assertIn("photo", message.lower())

	def test_a_photo_captured_on_the_phone_counts(self):
		"""The app posts the bytes, not a file that already exists on the server."""
		captured = {"attachment_name": "damage.jpg", "attachment": "aGVsbG8="}

		self.assertEqual(_missing_details([self._row(attach_photo=captured)]), "")
		self.assertTrue(_photo_of(self._row(attach_photo=captured)))

	def test_a_half_sent_photo_does_not_count(self):
		"""A name with no bytes, or bytes with no name, is not a photo."""
		for broken in ({"attachment_name": "damage.jpg"}, {"attachment": "aGVsbG8="}, {}):
			with self.subTest(photo=broken):
				self.assertFalse(_photo_of(self._row(attach_photo=broken)))
				self.assertIn("photo", _missing_details([self._row(attach_photo=broken)]).lower())

	def test_a_file_url_still_counts(self):
		self.assertTrue(_photo_of(self._row(attach_photo="/files/x.jpg")))
		self.assertFalse(_photo_of(self._row(attach_photo="   ")))

	def test_the_row_number_is_the_one_that_is_wrong(self):
		"""Scenario 9: several items in one submission."""
		message = _missing_details([self._row(), self._row(), self._row(size=None)])

		self.assertIn("Row 3", message)

	def test_a_row_with_no_item_is_named(self):
		self.assertIn("item", _missing_details([self._row(item_code=None)]).lower())

	def test_the_same_rules_bind_on_the_document(self):
		request = frappe.new_doc("Request for Material")
		request.type = INDIVIDUAL
		request.append("items", {"is_uniform_request": 1, "attach_photo": PHOTO, "qty": 1})

		with self.assertRaises(frappe.ValidationError) as raised:
			request.validate_uniform_request_details()

		self.assertIn("size", str(raised.exception).lower())


class TestTheDetailIsDemandedAtTheDecision(FrappeTestCase):
	"""Required Date and the line Description are needed to *leave* Pending Approval, not
	to enter it - the mobile form collects neither, and submits straight into that state.
	Read the other way round, no mobile request could ever be made."""

	def _pending(self, description=None, schedule_date=None):
		request = frappe.new_doc("Request for Material")
		request.type = INDIVIDUAL
		request.schedule_date = schedule_date
		request.append("items", {
			"is_uniform_request": 1, "size": SIZE, "attach_photo": PHOTO,
			"qty": 1, "requested_description": description,
		})
		return request

	def test_entering_pending_approval_needs_neither(self):
		request = self._pending()
		request.workflow_state = PENDING_APPROVAL

		request.validate_uniform_request_details()

	def test_leaving_it_needs_the_required_date(self):
		request = self._pending(description="Torn at the seam")
		request.workflow_state = "Approved"
		request._doc_before_save = self._pending()
		request._doc_before_save.workflow_state = PENDING_APPROVAL

		with self.assertRaises(frappe.ValidationError) as raised:
			request.validate_uniform_request_details()

		self.assertIn("Required Date", str(raised.exception))

	def test_leaving_it_needs_a_description(self):
		request = self._pending(schedule_date=frappe.utils.today())
		request.workflow_state = "Approved"
		request._doc_before_save = self._pending()
		request._doc_before_save.workflow_state = PENDING_APPROVAL

		with self.assertRaises(frappe.ValidationError) as raised:
			request.validate_uniform_request_details()

		self.assertIn("describe", str(raised.exception).lower())

	def test_a_complete_request_may_be_decided(self):
		request = self._pending(
			description="Torn at the seam", schedule_date=frappe.utils.today()
		)
		request.workflow_state = "Approved"
		request._doc_before_save = self._pending()
		request._doc_before_save.workflow_state = PENDING_APPROVAL

		request.validate_uniform_request_details()


class TestTheEndpointsShape(FrappeTestCase):
	def test_one_of_each_item(self):
		"""Scenario 5: the employee never types a quantity."""
		self.assertEqual(UNIFORM_QTY, 1)

	def test_it_raises_an_individual_request(self):
		self.assertEqual(INDIVIDUAL, "Individual")

	def test_it_goes_straight_for_approval(self):
		states = frappe.get_all(
			"Workflow Document State",
			filters={"parent": "RFM"},
			pluck="state",
		)
		self.assertIn(PENDING_APPROVAL, states)

	def test_the_approver_rule_is_not_duplicated(self):
		"""Scenario 7's approver - Reports To, else the site supervisor - is already in
		Request for Material, and the endpoint deliberately leaves it there."""
		source = frappe.read_file(frappe.get_app_path("one_fm", "api", "v2", "uniform_request.py"))

		self.assertNotIn("reports_to", source)
		self.assertNotIn("request_for_material_approver", source)


class TestTheServiceTile(FrappeTestCase):
	"""Scenario 1: the app builds its Requisition section from these records, so the icon
	does not exist until they do."""

	GROUP = "Requisition"
	SERVICE = "Uniform Request"

	def test_the_requisition_group_exists(self):
		if not frappe.db.exists("App Service Group", self.GROUP):
			self.skipTest("not migrated yet - the patch creates it")

		self.assertEqual(
			frappe.db.get_value("App Service Group", self.GROUP, "status"), "Active"
		)

	def test_the_uniform_request_tile_exists_and_is_offered_to_everyone(self):
		if not frappe.db.exists("App Service", self.SERVICE):
			self.skipTest("not migrated yet - the patch creates it")

		service = frappe.db.get_value(
			"App Service", self.SERVICE,
			["status", "service_group", "assign_to_timesheet_employees",
			 "assign_to_non_timesheet_employees"],
			as_dict=True,
		)

		self.assertEqual(service.status, "Active")
		self.assertEqual(service.service_group, self.GROUP)
		self.assertTrue(service.assign_to_timesheet_employees)
		self.assertTrue(service.assign_to_non_timesheet_employees)
