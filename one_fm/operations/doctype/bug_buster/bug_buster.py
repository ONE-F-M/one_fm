# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days

class BugBuster(Document):
	def validate(self):
		self.check_existing()

	def on_submit(self):
		self.update_roster()
	
	def check_existing(self):
		if frappe.db.exists("Bug Buster", {
			"from_date": ["BETWEEN", [self.from_date, self.to_date]],
			"docstatus": 1
			}):
			frappe.throw(f"""
				Rostered exist between {self.from_date} and {self.to_date}
			""")

	def update_roster(self):
		busters = frappe.get_single("Bug Buster Employee")
		buster_dict = {}
		buster_dict_id = {}
		for i in busters.employees:
			buster_dict[i.employee] = i
			buster_dict_id[i.order] = i
		current_buster = buster_dict.get(self.employee)
		if current_buster:
			if current_buster.order == len(busters.employees):
				busters.next_bug_buster = buster_dict_id[1].employee
				busters.full_name = buster_dict_id[1].employee_name
			else:
				next_buster = buster_dict_id[current_buster.order+1]
				busters.next_bug_buster = next_buster.employee
				busters.full_name = next_buster.employee_name
			busters.from_date = add_days(self.to_date, 1)
			busters.to_date = add_days(self.to_date, 7)
			busters.save()

			self.send_email()
		else:
			pass

	def send_email(self):
		frappe.sendmail(
			recipients=frappe.db.get_value("Employee", self.employee, "user_id"),
			subject="Bug Buster Assigned",
			message=f"""
				You have the assigned the role of a Bug Buster from {self.from_date} to {self.to_date}. 
				Weldone Solder!.
			""",
		)


def roster_bug_buster():
	today = getdate()
	tomorrow = add_days(today, 1)
	if today.strftime('%A') == 'Tuesday':
		busters = frappe.get_single("Bug Buster Employee")
		frappe.get_doc({
			"doctype":"Bug Buster",
			"employee":busters.next_bug_buster,
			"from_date": tomorrow,
			"to_date": add_days(tomorrow, 6)
		}).submit()