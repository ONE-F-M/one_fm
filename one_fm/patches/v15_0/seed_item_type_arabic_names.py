"""WI-002399: the two Item Type translations the design document supplies.

The Proof of Work letter names the contract's services in Arabic, read from
Item Type.arabic_name. Only these two are written down anywhere - Security Guard and
Cleaner, from the letter's own example - so only these two are seeded; the rest are for
whoever knows the wording to fill in, which is why the field is on the master rather
than in a mapping in the code.

Only fills what is empty. A translation somebody has already typed is theirs.
"""

import frappe

ARABIC_NAMES = {
	"Security Guard": "حارس أمن",
	"Cleaner": "فراش",
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
