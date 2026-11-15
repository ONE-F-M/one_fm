from one_fm.custom.workflow.workflow import create_workflow_state

# Set by the HR Enquiry Lifecycle process. HR Enquiry has no Frappe Workflow, so the
# process writes these straight into workflow_state, a Link that needs the records.
STATES = (
	("Awaiting Employee Response", "Warning"),
	("Under HR Review", "Info"),
	("Decided", "Success"),
)


def execute():
	create_workflow_state([{"workflow_state_name": state, "style": style} for state, style in STATES])
