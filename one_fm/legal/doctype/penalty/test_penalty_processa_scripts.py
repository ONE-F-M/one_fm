# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Penalty process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Notify Penalty Recipient": """# Tells the employee a penalty has been issued to them.
from one_fm.api.notification import create_notification_log

if doc.recipient_user:
	subject = frappe._("Penalty Issued by {0}.").format(doc.issuer_name or "Administrator")
	message = frappe._("You have been issued a penalty.<br>Link: {0}").format(frappe.utils.get_link_to_form(doc.doctype, doc.name))
	create_notification_log(subject, message, [doc.recipient_user], doc)
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Penalty",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


def penalty(**kw):
	doc = frappe.new_doc("Penalty")
	doc.name = "PEN-PROCESSA-TEST-1"
	doc.update({"issuer_name": "Issuer", **kw})
	return doc


class TestNotifyPenaltyRecipient(FrappeTestCase):
	@patch("one_fm.api.notification.create_notification_log")
	def test_notifies_the_recipient_user(self, notify):
		run("Notify Penalty Recipient", penalty(recipient_user="someone@example.com"))
		notify.assert_called_once()
		subject, _message, users, _doc = notify.call_args[0]
		self.assertEqual(users, ["someone@example.com"])
		self.assertIn("Issuer", subject)

	@patch("one_fm.api.notification.create_notification_log")
	def test_skips_a_penalty_without_recipient_user(self, notify):
		run("Notify Penalty Recipient", penalty(recipient_user=""))
		notify.assert_not_called()


class TestControllerLeavesNotificationToTheMap(FrappeTestCase):
	def test_no_after_insert_hook(self):
		from one_fm.legal.doctype.penalty.penalty import Penalty
		self.assertFalse(hasattr(Penalty, "after_insert"))
