"""WI-002399: take back the one Arabic service name that was guessed.

The Proof of Work letter went out with "Tea Boy" printed in English in the middle of its
Arabic paragraph, and the fix seeded عامل ضيافة on the Item Type. The wording was a
guess - no design document carries it - and the letter reads the PAM designation the
staff on that Sale Item are actually registered under instead, which for a tea boy is
فراش. A guessed translation on the master would outrank it, because a name somebody
typed is meant to win.

Only clears the guess. A translation anybody has since typed over it is theirs and stays.
"""

import frappe

GUESSED = "عامل ضيافة"


def execute():
	if frappe.db.get_value("Item Type", "Tea Boy", "arabic_name") != GUESSED:
		return

	frappe.db.set_value("Item Type", "Tea Boy", "arabic_name", "", update_modified=False)
	print("WI-002399: cleared the guessed Arabic name on Item Type Tea Boy")
