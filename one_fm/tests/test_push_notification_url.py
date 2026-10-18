from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.api import api
from one_fm.one_fm.doctype.employee_resignation.employee_resignation import EmployeeResignation
from one_fm.utils import send_push_notification


class _FakeResignation:
	"""Just enough of an Employee Resignation for notify_employee_app."""
	employee = "HR-EMP-0001"
	name = "HR-RES-0001"

	def get(self, key):
		return {"workflow_state": "Approved"}.get(key)


class TestPushNotificationUrl(FrappeTestCase):
	"""Every push notification carries data.url; firebase send is mocked."""

	def setUp(self):
		super().setUp()
		self.employee_row = frappe._dict(fcm_token="token-123", device_os="Android")
		patches = [
			patch("firebase_admin.messaging.send", return_value="msg-id"),
			patch.object(api, "initialize_firebase"),
			patch("frappe.db.get_value", return_value=self.employee_row),
		]
		self.send = patches[0].start()
		for p in patches[1:]:
			p.start()
		for p in patches:
			self.addCleanup(p.stop)

	def sent_data(self):
		self.assertEqual(self.send.call_count, 1)
		message = self.send.call_args[0][0]
		return message.data

	def test_default_url_is_notification(self):
		self.assertTrue(send_push_notification("HR-EMP-0001", "Title", "Body"))
		self.assertEqual(self.sent_data(), {"url": "/notification"})

	def test_default_url_added_to_existing_data_without_changing_keys(self):
		send_push_notification("HR-EMP-0001", "Title", "Body", data={"type": "x", "count": 3})
		self.assertEqual(self.sent_data(), {"type": "x", "count": "3", "url": "/notification"})

	def test_caller_url_is_kept(self):
		send_push_notification("HR-EMP-0001", "Title", "Body", data={"url": "/custom"})
		self.assertEqual(self.sent_data()["url"], "/custom")

	def test_leave_application_url(self):
		api.push_notification_rest_api_for_leave_application("HR-EMP-0001", "Leave", "Approved", "HR-LAP-2026-00001")
		self.assertEqual(self.sent_data()["url"], "/leaves/HR-LAP-2026-00001")

	def test_resignation_url(self):
		EmployeeResignation.notify_employee_app(_FakeResignation(), "Resignation Approved", "Approved")
		data = self.sent_data()
		self.assertEqual(data["url"], "/resignation")
		self.assertEqual(data["type"], "resignation_update")
		self.assertEqual(data["resignation"], "HR-RES-0001")
		self.assertEqual(data["workflow_state"], "Approved")

	def test_checkin_rest_url(self):
		api.push_notification_rest_api_for_checkin("HR-EMP-0001", "Check in", "Reminder", "true", "false", "false")
		self.assertEqual(self.sent_data()["url"], "/checkin")

	def test_checkin_url_with_buttons(self):
		api.push_notification_for_checkin("HR-EMP-0001", "Check in", "Reminder", "true", "false", "false")
		data = self.sent_data()
		self.assertEqual(data["url"], "/checkin")
		self.assertEqual(data["showButtonCheckIn"], "true")
		self.assertEqual(data["showButtonCheckOut"], "false")
		self.assertEqual(data["showButtonArrivingLate"], "false")
