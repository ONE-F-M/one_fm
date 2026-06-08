# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BonusRequestItems(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approve: DF.Check
		bonus_amount: DF.Currency
		department: DF.Link | None
		description: DF.SmallText | None
		designation: DF.Link | None
		employee: DF.Link
		employee_id: DF.Data | None
		employee_name: DF.Data | None
		justification: DF.Literal[
			"",
			"Excellent Performance",
			"Grooming reward",
			"Perfect Attendance",
			"Client Appreciation",
			"Long Service",
			"Seasonal Bonus",
			"Special Recognition",
			"Other",
		]
		operations_site: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project: DF.Link | None
		reject: DF.Check
	# end: auto-generated types

	pass
