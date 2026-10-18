# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The HD Ticket Client Script is deleted only when it is the old Jira ticket button."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.delete_jira_ticket_client_script import execute


class TestDeleteJiraTicketClientScript(FrappeTestCase):
	def _client_script(self, script):
		frappe.delete_doc("Client Script", "HD Ticket", ignore_missing=True)
		frappe.get_doc(
			{"doctype": "Client Script", "name": "HD Ticket", "dt": "HD Ticket", "enabled": 0, "script": script}
		).db_insert()

	def test_the_jira_ticket_button_script_is_deleted(self):
		self._client_script('frappe.call({method: "one_fm.overrides.hd_ticket.create_jira_ticket"});')
		execute()
		self.assertFalse(frappe.db.exists("Client Script", "HD Ticket"))

	def test_another_hd_ticket_script_is_kept(self):
		self._client_script('frappe.ui.form.on("HD Ticket", {});')
		execute()
		self.assertTrue(frappe.db.exists("Client Script", "HD Ticket"))
