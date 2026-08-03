# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Mark guidelines in the register as input material.

``AI Reference Index`` holds two different kinds of thing. Most rows are
controlled documents the process *produced* — they carry a document code, a
version history and a lifecycle. Guidelines are the opposite: they are material
the process *reads*, catalogued so a requester can point at one as the basis for
a new document. The same is now true of the New Content Document a revision is
built from.

Until the ``is_input_material`` flag existed there was nothing to tell them
apart, so guidelines showed up wherever controlled documents were offered —
including as things you could revise or withdraw. This marks them.

Guidelines are input by construction in this process: the Create path exists to
turn one into a Policy, SOP or Manual. Nothing else is touched, so a row that
was genuinely published as a Guideline-type controlled document can simply have
the flag cleared by hand.
"""

import frappe


def execute():
	frappe.reload_doc("one_fm", "doctype", "ai_reference_index")

	guidelines = frappe.get_all(
		"AI Reference Index",
		filters={"document_type": "Guideline", "is_input_material": 0},
		pluck="name",
	)
	if not guidelines:
		print("No Guideline entries to flag as input material.")
		return

	for name in guidelines:
		# update_modified=False: the flag is a classification of what the row
		# always was, not an edit to the document. Bumping `modified` would hand
		# a stale-document error to anyone with the form open and would make the
		# register look freshly touched in every report sorted by modified.
		frappe.db.set_value("AI Reference Index", name, "is_input_material", 1, update_modified=False)

	frappe.db.commit()
	print(f"Flagged {len(guidelines)} Guideline entr(ies) as input material: {', '.join(guidelines)}")
