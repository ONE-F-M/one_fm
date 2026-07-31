import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

WORKFLOW = "Penalty & Investigation"
WORKFLOW_FILE = "penalty_and_investigation.json"


def execute():
	"""Apply the supplied Penalty And Investigation workflow (WI-001796).

	Workflows are only created by the installer, so an existing site needs the states
	and transitions applied here. The definition reuses the active workflow's name so
	it replaces it: two active workflows on one doctype conflict.

	Safe on the current data - every record sits in Draft, which the definition still
	carries - but any record found in a retired state is reported rather than silently
	left unusable.
	"""
	definition = get_workflow_json_file(WORKFLOW_FILE)

	create_workflow(definition)

	# create_workflow logs its failures instead of raising, so confirm the result
	# rather than trusting it: a half-applied workflow leaves the doctype ungoverned.
	expected = {state["state"] for state in definition["states"]}
	applied = set(
		frappe.get_all(
			"Workflow Document State", filters={"parent": WORKFLOW}, pluck="state"
		)
	)
	missing = expected - applied
	if missing:
		frappe.throw(
			f"Workflow {WORKFLOW!r} was not fully applied; missing states: {sorted(missing)}. "
			"Check the Error Log for 'Workflow Creation Error'."
		)

	frappe.db.commit()

	stranded = frappe.db.sql(
		"""
		select ifnull(workflow_state, '') as state, count(*) as n
		from `tabPenalty And Investigation`
		group by workflow_state
		""",
		as_dict=True,
	)
	orphans = [r for r in stranded if r.state and r.state not in applied]
	for row in orphans:
		print(
			f"WI-001796: {row.n} Penalty And Investigation record(s) remain in retired "
			f"state {row.state!r} - these need reassigning to a current state"
		)
	if not orphans:
		print(f"WI-001796: workflow applied ({len(applied)} states); no records stranded")
