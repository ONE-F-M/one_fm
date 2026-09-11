"""WI-002399: the Item Type translations the Proof of Work letter needs today.

The letter names the contract's services in Arabic, read from Item Type.arabic_name.
Security Guard and Cleaner are the design document's own examples. Tea Boy was added
after the letter went out with "Tea Boy" printed in English in the middle of the Arabic
paragraph - it is the only other type any Proof of Work uses, and عامل ضيافة is the
contract wording for the role. Nothing else is seeded: the rest are for whoever knows
the wording to fill in, which is why the field is on the master rather than in a mapping
in the code, and why anyone can correct the wording without a deploy.

Only fills what is empty. A translation somebody has already typed is theirs, so this
re-runs safely.
"""

import frappe

ARABIC_NAMES = {
	"Security Guard": "حارس أمن",
	"Cleaner": "فراش",
	"Tea Boy": "عامل ضيافة",
}


def execute():
	frappe.reload_doc("purchase", "doctype", "item_type")

	filled = 0
	for item_type, arabic in ARABIC_NAMES.items():
		if not frappe.db.exists("Item Type", item_type):
			continue
		if frappe.db.get_value("Item Type", item_type, "arabic_name"):
			continue
		frappe.db.set_value("Item Type", item_type, "arabic_name", arabic, update_modified=False)
		filled += 1

	print(f"WI-002399: filled the Arabic name on {filled} Item Type(s)")
