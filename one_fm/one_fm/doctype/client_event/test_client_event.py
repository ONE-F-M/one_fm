# Copyright (c) 2025, ONE FM and Contributors
# See license.txt
"""The checks the Client Event Lifecycle process runs as script tasks.

The Server Scripts live on the site and move between sites with the process export, so
their bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that
has drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, nowdate

PAST_START = "The scheduled event time must be current or future date/time. Please adjust the event details."
PAST_END = "The scheduled end date/time must be current or future date/time. Please adjust the event details."
END_BEFORE_START = "The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details."

SCRIPTS = {
	"Validate Client Event": """# Checks made when the event is submitted for review: it is scheduled for today or later
# and ends after it starts, and an extension neither repeats another extension of the same
# event nor starts before that event ends.
getdate = frappe.utils.getdate
get_datetime = frappe.utils.get_datetime
today = getdate(frappe.utils.today())
errors = []

if (doc.start_date and getdate(doc.start_date) < today) or (
	doc.event_start_datetime and getdate(doc.event_start_datetime) < today
):
	errors.append(frappe._("The scheduled event time must be current or future date/time. Please adjust the event details."))

if (doc.end_date and getdate(doc.end_date) < today) or (
	doc.event_end_datetime and getdate(doc.event_end_datetime) < today
):
	errors.append(frappe._("The scheduled end date/time must be current or future date/time. Please adjust the event details."))

if (doc.start_date and doc.end_date and get_datetime(doc.end_date) < get_datetime(doc.start_date)) or (
	doc.event_start_datetime
	and doc.event_end_datetime
	and get_datetime(doc.event_end_datetime) < get_datetime(doc.event_start_datetime)
):
	errors.append(frappe._("The scheduled end date/time must be later than Start Date or Start Datetime. Please adjust the event details."))

if doc.is_extension_request and doc.original_client_event:
	if frappe.db.exists(
		"Client Event",
		{"original_client_event": doc.original_client_event, "name": ["!=", doc.name], "docstatus": ["<", 2]},
	):
		errors.append(
			frappe._("An extension request already exists for the original Client Event {0}.").format(doc.original_client_event)
		)

	original = frappe.db.get_value(
		"Client Event", doc.original_client_event, ["end_date", "event_end_datetime"], as_dict=True
	)
	if original and (
		(doc.event_start_datetime and original.event_end_datetime and get_datetime(doc.event_start_datetime) < get_datetime(original.event_end_datetime))
		or (doc.start_date and original.end_date and getdate(doc.start_date) < getdate(original.end_date))
	):
		errors.append(
			frappe._("The extension's Start Date and Time cannot be earlier than the Original Client Event's End Date and Time.")
		)

if errors:
	frappe.msgprint("<br>".join(errors), title=frappe._("Client Event"), indicator="red")

result["client_event_valid"] = not errors
""",
	"Validate Client Event Decision": """# An event that has already taken place can only be approved, and an event that has
# started can no longer go back to draft.
getdate = frappe.utils.getdate
action = task_data.get("action")
errors = []

if doc.start_date and doc.end_date:
	today = getdate(frappe.utils.today())
	started = today >= getdate(doc.start_date)
	finished = today > getdate(doc.end_date)

	if finished and action in ("Reject", "Return To Draft"):
		errors.append(
			frappe._("You are unable to {0} this client event as the event has already taken place. Please approve.").format(
				"reject" if action == "Reject" else "return to draft"
			)
		)
	elif finished and action == "Cancel":
		errors.append(frappe._("You are unable to cancel this client event as the event has already taken place."))
	elif started and action == "Return To Draft":
		errors.append(frappe._("You are unable to return this client event to draft as the event has already started. Please approve."))

if errors:
	frappe.msgprint("<br>".join(errors), title=frappe._("Client Event"), indicator="red")

result["client_event_decision_valid"] = not errors
""",
}


def run(script_name, doc, action=None):
	"""Run a script the way the BPMN engine does; return its result and the messages shown."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": {"action": action},
		"result": result,
		"context_doctype": "Client Event",
		"context_docname": doc.name,
	}
	with patch("frappe.msgprint") as msgprint:
		exec(SCRIPTS[script_name], namespace)
	shown = " ".join(str(c.args[0]) for c in msgprint.call_args_list)
	return result, shown


def make_event(**kwargs):
	doc = frappe.new_doc("Client Event")
	doc.name = kwargs.pop("name", "CE-PROCESSA-TEST-1")
	doc.update({
		"event_name": "Test Event",
		"start_date": add_days(nowdate(), 1),
		"event_start_datetime": add_to_date(now_datetime(), days=1),
		"end_date": add_days(nowdate(), 2),
		"event_end_datetime": add_to_date(now_datetime(), days=2),
	})
	doc.update(kwargs)
	return doc


class TestClientEventSubmissionCheck(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back per class, so fixtures from an earlier test are still here.
		frappe.db.delete("Client Event", {"name": ["like", "CE-PROCESSA-TEST-%"]})

	def assert_refused(self, doc, message):
		result, shown = run("Validate Client Event", doc)
		self.assertFalse(result["client_event_valid"])
		self.assertIn(message, shown)

	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)

	def test_valid_dates(self):
		result, _shown = run("Validate Client Event", make_event())
		self.assertTrue(result["client_event_valid"])

	def test_start_date_in_past(self):
		self.assert_refused(make_event(start_date=add_days(nowdate(), -1)), PAST_START)

	def test_event_start_datetime_in_past(self):
		self.assert_refused(make_event(event_start_datetime=add_to_date(now_datetime(), days=-1)), PAST_START)

	def test_end_date_in_past(self):
		self.assert_refused(make_event(end_date=add_days(nowdate(), -1)), PAST_END)

	def test_event_end_datetime_in_past(self):
		self.assert_refused(make_event(event_end_datetime=add_to_date(now_datetime(), days=-1)), PAST_END)

	def test_end_date_before_start_date(self):
		self.assert_refused(make_event(start_date=add_days(nowdate(), 2), end_date=add_days(nowdate(), 1)), END_BEFORE_START)

	def test_event_end_datetime_before_event_start_datetime(self):
		self.assert_refused(
			make_event(event_start_datetime=add_to_date(now_datetime(), days=2), event_end_datetime=add_to_date(now_datetime(), days=1)),
			END_BEFORE_START,
		)

	def test_an_extension_starts_after_the_event_it_extends(self):
		original = make_event(name="CE-PROCESSA-TEST-0", end_date=add_days(nowdate(), 5), event_end_datetime=add_to_date(now_datetime(), days=5))
		original.db_insert()
		self.assert_refused(make_event(is_extension_request=1, original_client_event=original.name), "cannot be earlier")
		later = make_event(
			is_extension_request=1, original_client_event=original.name, start_date=add_days(nowdate(), 6),
			event_start_datetime=add_to_date(now_datetime(), days=6), end_date=add_days(nowdate(), 7), event_end_datetime=add_to_date(now_datetime(), days=7),
		)
		result, _shown = run("Validate Client Event", later)
		self.assertTrue(result["client_event_valid"])

	def test_an_event_is_extended_once(self):
		original = make_event(name="CE-PROCESSA-TEST-0")
		original.db_insert()
		first = make_event(name="CE-PROCESSA-TEST-2", is_extension_request=1, original_client_event=original.name)
		first.db_insert()
		self.assert_refused(make_event(is_extension_request=1, original_client_event=original.name), "already exists")


class TestClientEventDecisionCheck(FrappeTestCase):
	def decide(self, action, start, end):
		return run("Validate Client Event Decision", make_event(start_date=add_days(nowdate(), start), end_date=add_days(nowdate(), end)), action)[0]["client_event_decision_valid"]

	def test_a_future_event_can_be_rejected_returned_or_cancelled(self):
		for action in ("Reject", "Return To Draft", "Cancel"):
			self.assertTrue(self.decide(action, 1, 2), action)

	def test_a_finished_event_can_only_be_approved(self):
		for action in ("Reject", "Return To Draft", "Cancel"):
			self.assertFalse(self.decide(action, -3, -1), action)

	def test_an_event_under_way_cannot_go_back_to_draft(self):
		self.assertFalse(self.decide("Return To Draft", -1, 1))
		self.assertTrue(self.decide("Reject", -1, 1))
		self.assertTrue(self.decide("Cancel", -1, 1))
