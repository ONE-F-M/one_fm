# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RoutineTaskProcess(Document):
	pass

@frappe.whitelist()
def filter_routine_document(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			routine_task_document
		from
			`tabRoutine Task Document`
		where
			parent='Routine Document' and routine_task_document like %(txt)s
			limit %(start)s, %(page_len)s
	"""
	return frappe.db.sql(query,
		{
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)
