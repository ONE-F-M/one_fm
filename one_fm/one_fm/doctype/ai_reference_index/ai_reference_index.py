# Copyright (c) 2026, one-fm and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AIReferenceIndex(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.LongText | None
		document_type: DF.Data | None
		drive_file_id: DF.Data
		drive_file_link: DF.Data | None
		source_process: DF.Data | None
		title: DF.Data
	# end: auto-generated types
	pass
