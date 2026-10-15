"""Mark the overtime schedules that were held for double-shift approval before the marker existed.

``dsot_request`` is what tells a double-shift overtime (DSOT) schedule from ordinary
overtime. It is set when a row is held and never cleared, but rows held before the field
shipped carry nothing. The DSOT report counts only rows where it is set, so without this
the schedules that are pending or rejected now, and the ones already approved, would not
appear in it.

A row is a DSOT if it is Over-Time and either it is Pending DSOT Approval or Rejected right
now, or its Version history shows it was once Pending DSOT Approval (an approved one is
Active today and looks like any other overtime row). Active alone proves nothing.

The marker is set to the schedule's own name, the same "request of one" grouping the DSOT
notifications already use for a schedule held on its own.
"""

import frappe
from frappe.query_builder import DocType, functions as fn
from frappe.utils import create_batch

ROSTER_TYPE = "Over-Time"
HELD_STATES = ("Pending DSOT Approval", "Rejected")
PENDING = "Pending DSOT Approval"
BATCH_SIZE = 1000


def execute():
	if not frappe.db.has_column("Employee Schedule", "dsot_request"):
		# The column arrives with the field itself. Without it there is nothing to mark.
		return

	names = get_held_now() | get_once_held(get_versioned_names())

	for batch in create_batch(sorted(names), BATCH_SIZE):
		mark_as_request_of_one(batch)


def get_held_now():
	Schedule = DocType("Employee Schedule")

	return set(
		(
			frappe.qb.from_(Schedule)
			.select(Schedule.name)
			.where(Schedule.roster_type == ROSTER_TYPE)
			.where(fn.IfNull(Schedule.dsot_request, "") == "")
			.where(Schedule.workflow_state.isin(HELD_STATES))
		).run(pluck=True)
	)


def get_versioned_names():
	"""Names of schedules whose version log mentions the pending state.

	Version data is compact JSON, so the state appears as ``"Pending DSOT Approval"``.
	"""
	Version = DocType("Version")

	return set(
		(
			frappe.qb.from_(Version)
			.select(Version.docname)
			.distinct()
			.where(Version.ref_doctype == "Employee Schedule")
			.where(Version.data.like(f"%{PENDING}%"))
		).run(pluck=True)
	)


def get_once_held(candidates):
	"""Of the versioned schedules, those that are Over-Time and not yet marked."""
	Schedule = DocType("Employee Schedule")
	names = set()

	for batch in create_batch(sorted(candidates), BATCH_SIZE):
		names.update(
			(
				frappe.qb.from_(Schedule)
				.select(Schedule.name)
				.where(Schedule.name.isin(batch))
				.where(Schedule.roster_type == ROSTER_TYPE)
				.where(fn.IfNull(Schedule.dsot_request, "") == "")
			).run(pluck=True)
		)

	return names


def mark_as_request_of_one(batch):
	Schedule = DocType("Employee Schedule")

	(
		frappe.qb.update(Schedule)
		.set(Schedule.dsot_request, Schedule.name)
		.where(Schedule.name.isin(batch))
		.where(fn.IfNull(Schedule.dsot_request, "") == "")
	).run()

	frappe.db.commit()  # nosemgrep: one batch of marked rows is one unit of work
