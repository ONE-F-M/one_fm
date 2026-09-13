# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The request to cancel a visa that has already been issued.

The DocType is the BA site's, field for field (WI-002425). What is here in code is the two
rules stacked on top of it: one live cancellation per Visa Request (WI-002432), and the
reason the request was raised for (WI-002428).

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

# WI-002428: the reasons the popup offers. The BA site has no reason field at all, so this
# is not a migration of theirs - it is what the story asks for, and it starts with the one
# reason any criterion names. The others are the business's to add.
EXPIRY_REASON = "Cancellation Due to Visa Expiry"

# WI-002431: only a visa that was actually issued can expire, and Completed is the state
# the Visa Request workflow gives that.
COMPLETED_STATE = "Completed"


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


# What a cancellation carries over from the visa it cancels. Same fieldname on both sides,
# so the copy is a loop rather than a map. The BA site types four of these as Data where
# the Visa Request has a Date - passport and visa dates - which is their shape, so the
# values are stringified on the way rather than the field being "corrected" here.
COPIED_FROM_VISA_REQUEST = (
	"job_applicant_full_name",
	"grd_operator",
	"passport_copy",
	"passport_number",
	"passport_holder_of",
	"passport_issued_on",
	"passport_expires_on",
	"pam_reference_number",
	"visa_reference_number",
	"visa_issue_date",
	"visa_expiry_date",
	"visa_document",
)


def build_cancellation(visa_request, cancellation_reason: str):
	"""A Draft cancellation for this visa, unsaved.

	Returned rather than inserted so both callers - the button and the expiry job - decide
	for themselves how to handle a refusal.
	"""
	doc = frappe.new_doc("Visa Cancellation Request")
	doc.visa_request_id = visa_request.name
	doc.cancellation_reason = cancellation_reason

	for fieldname in COPIED_FROM_VISA_REQUEST:
		value = visa_request.get(fieldname)
		if value is not None:
			doc.set(fieldname, value)

	return doc


@frappe.whitelist(methods=["POST"])
def create_from_visa_request(visa_request: str, cancellation_reason: str):
	"""Raise a cancellation for a visa, with the reason the user picked (WI-002428).

	The reason is demanded here as well as in the dialog: the dialog is a convenience, and
	a method that trusted it would let the process be started without one through any
	other caller.
	"""
	if not cancellation_reason:
		frappe.throw(
			_("Select a reason for the cancellation before raising the request."),
			title=_("Cancellation Reason Required"),
		)

	source = frappe.get_doc("Visa Request", visa_request)
	source.check_permission("read")

	if not frappe.has_permission("Visa Cancellation Request", "create"):
		frappe.throw(
			_("You do not have permission to create a Visa Cancellation Request."),
			frappe.PermissionError,
		)

	doc = build_cancellation(source, cancellation_reason)
	doc.insert()

	return {"name": doc.name}


def expired_visas(on_date=None):
	"""Completed visas whose expiry date has arrived, for somebody not yet employed.

	Completed because that is the state the Visa Request workflow gives a visa that was
	actually issued - a draft or rejected request has no visa to cancel, whatever date it
	carries.

	On or before the date rather than exactly on it, so a day the scheduler missed is still
	caught rather than leaving that visa uncancelled for good. Raising one is idempotent:
	the duplicate rule refuses a second.

	An applicant who has become an Employee is skipped, which is the story's own condition -
	they are here and working, so the visa is not one to cancel behind them.
	"""
	requests = frappe.get_all(
		"Visa Request",
		filters=[
			["workflow_state", "=", COMPLETED_STATE],
			["visa_expiry_date", "is", "set"],
			["visa_expiry_date", "<=", getdate(on_date or today())],
		],
		fields=["name", "job_applicant"],
	)

	return [
		row.name
		for row in requests
		if not (row.job_applicant and frappe.db.exists("Employee", {"job_applicant": row.job_applicant}))
	]


def cancel_expired_visas():
	"""Daily: raise a cancellation for every visa that has reached its expiry (WI-002431).

	Left in Draft, which is what the story asks for - the process map takes it from there.

	One failure does not stop the rest, and a visa that already has a live cancellation is
	refused by the duplicate rule rather than checked for twice here.
	"""
	raised = []

	for name in expired_visas():
		try:
			source = frappe.get_doc("Visa Request", name)
			if live_cancellation(name):
				continue

			doc = build_cancellation(source, EXPIRY_REASON)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			raised.append(doc.name)
		except Exception:
			frappe.log_error(
				title=f"Could not raise the expiry cancellation for {name}",
				message=frappe.get_traceback(),
			)
			continue

	if raised:
		frappe.db.commit()

	return raised
