import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

WORKFLOW = "Penalty & Investigation"
WORKFLOW_FILE = "penalty_and_investigation.json"

# Frappe needs a Workflow State master per state name before a Workflow can link to
# it. The shared helper tries to create them but swallows its own failures into the
# Error Log, so they are created here where a problem can actually be raised.
STATE_STYLES = {
	"Draft": "",
	"Pending HR Administrator": "Warning",
	"Pending Legal Manager": "Warning",
	"Pending General Manager": "Warning",
	"On Hold": "Warning",
	"Approved": "Success",
	"Rejected": "Danger",
	"Cancelled": "Danger",
}


def execute():
	"""Replace the Penalty And Investigation workflow (WI-001796).

	Workflows are only created by the installer, so an existing site needs the new
	states and transitions applied here. It reuses the active workflow's name so it
	replaces it: two active workflows on one doctype conflict.

	Safe on the current data - every record sits in Draft, which the new workflow still
	defines - but any record found in a retired state is reported rather than silently
	left unusable.
	"""
	for state, style in STATE_STYLES.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)

	create_workflow(get_workflow_json_file(WORKFLOW_FILE))

	# create_workflow logs its failures instead of raising, so confirm the result
	# rather than trusting it: a half-applied workflow leaves the doctype ungoverned.
	applied = set(
		frappe.get_all(
			"Workflow Document State", filters={"parent": WORKFLOW}, pluck="state"
		)
	)
	missing = set(STATE_STYLES) - applied
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
