"""HD-1888665: the 69 policies WI-002494 left behind.

WI-002494 renamed "Apply Online by PRO" to "Apply Online by GR Operator" and moved the
502 applications waiting in it. It did not touch create_mi_record, which went on writing
the old name straight into the row with db_set - so every renewal opened since has landed
in a state the workflow does not have: no action out of it, and `status` left blank
because no workflow state was there to write it.

They go to Draft rather than to the renamed state. Each was inserted in Draft and pushed
out of it by the db_set, so the open Workflow Action beside every one of them already
says Draft, and the GRO assignment rule has had them on their owner's desk the whole
time. Draft is the state the rest of the record already agrees on.
"""

import frappe

DOCTYPE = "Medical Insurance"
OLD_STATE = "Apply Online by PRO"
DRAFT = "Draft"


def execute():
	frappe.db.set_value(
		DOCTYPE,
		{"workflow_state": OLD_STATE},
		{"workflow_state": DRAFT, "status": DRAFT},
		update_modified=False,
	)
	verify()


def verify():
	stranded = frappe.db.count(DOCTYPE, {"workflow_state": OLD_STATE})
	if stranded:
		frappe.throw(
			f"HD-1888665: {stranded} {DOCTYPE} records still hold {OLD_STATE!r}, which has "
			"no transition out of it."
		)
