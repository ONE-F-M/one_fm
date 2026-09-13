# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The request to cancel a visa that has already been issued.

The DocType is the BA site's, field for field (WI-002425). What is here in code is the
rule stacked on top of it: one live cancellation per Visa Request (WI-002432).

The lifecycle itself is the Visa Cancellation process map, which is configured separately -
nothing here decides which state the request moves to next.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

# WI-002432: the state that frees a Visa Request to be cancelled again. It is a Workflow
# State the Visa Cancellation process map configures rather than one this app defines, so
# it is named here as a string and checked against that master in the tests - a rename
# there would otherwise switch the escape hatch off silently.
REJECTED_STATE = "Visa Cancellation Rejected"


def has_workflow_state_column() -> bool:
	"""Does this site have the workflow_state column yet?

	Frappe creates it as a Custom Field when a workflow is first attached to the doctype,
	and the Visa Cancellation workflow arrives with the process map rather than with this
	app. Filtering on a column that is not there yet would fail the whole query, so the
	duplicate rule asks first - the same guard the roster uses for Employee Schedule.
	"""
	return "workflow_state" in frappe.db.get_table_columns("Visa Cancellation Request")


def live_cancellation_filters(visa_request: str, exclude=None) -> list:
	"""Which cancellations against this Visa Request are even candidates (WI-002432).

	A cancelled document is not one of them - it has been withdrawn. The state is not asked
	for here: see live_cancellation().
	"""
	return [
		["visa_request_id", "=", visa_request],
		# `exclude or ""` rather than the name itself: a document validated before a name
		# has been allocated would make that clause `name != NULL`, which matches nothing
		# in SQL and would switch the whole rule off.
		["name", "!=", exclude or ""],
		["docstatus", "!=", 2],
	]


def is_standing(workflow_state) -> bool:
	"""Does this cancellation still stand, or has the process map refused it?

	"Visa Cancellation Rejected" is the story's escape hatch: the PRO Operator refused this
	attempt, so another may be raised.

	Asked in Python rather than in the query on purpose. A cancellation that has not yet
	entered the process carries no state at all, and `workflow_state != 'Visa Cancellation
	Rejected'` is NULL in SQL for those rows - so a filtered query would quietly stop
	finding exactly the fresh drafts the popup and the expiry job create, and let duplicates
	straight through.
	"""
	return workflow_state != REJECTED_STATE


def live_cancellation(visa_request: str, exclude: str | None = None) -> str | None:
	"""The cancellation already standing against this Visa Request, if any (WI-002432)."""
	if not visa_request:
		return None

	fields = ["name"]
	# The column only exists once a workflow is attached to the doctype. Where it is not
	# there yet, nothing has a state and every candidate stands.
	if has_workflow_state_column():
		fields.append("workflow_state")

	for row in frappe.get_all(
		"Visa Cancellation Request",
		filters=live_cancellation_filters(visa_request, exclude),
		fields=fields,
	):
		if is_standing(row.get("workflow_state")):
			return row.name

	return None


class VisaCancellationRequest(Document):
	def validate(self):
		self.validate_no_live_cancellation()

	def validate_no_live_cancellation(self):
		"""One live cancellation per Visa Request (WI-002432).

		Only on the way in, and for the same reason the Visa Request rule is: an existing
		request re-checked on every save would find itself and become unsaveable.

		The rule is on the document rather than on the button, so it holds however the
		request was raised - by hand, from the Visa Request popup, or by the expiry job.
		That is what the story's note asks for in as many words.
		"""
		if not self.is_new():
			return

		existing = live_cancellation(self.visa_request_id, exclude=self.name)
		if not existing:
			return

		frappe.throw(
			_(
				"A Visa Cancellation Request already exists for {0}: {1}. Only one can "
				"stand at a time - another can be raised once that one has been rejected."
			).format(
				frappe.bold(self.visa_request_id),
				frappe.utils.get_link_to_form("Visa Cancellation Request", existing),
			),
			title=_("Visa Cancellation Request Already Exists"),
		)
