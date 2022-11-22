# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe.utils import getdate, get_last_day, get_first_day
from frappe.model.document import Document
from one_fm.utils import get_week_start_end

class PostSchedulerChecker(Document):
	def autoname(self):
		self.name = f"{self.contract}-{str(getdate())}"
	def before_insert(self):
		name = f"{self.contract}-{str(getdate())}"
		if frappe.db.exists(self.doctype, {'name': name}):
			frappe.get_doc(self.doctype, name).delete()

	def validate(self):
		if not self.check_date:
			self.check_date = getdate()
		self.fill_items()
		self.get_supervisor()
		if not self.items:
			frappe.throw('No issues found.')

	def after_insert(self):
		frappe.db.commit()

	def get_supervisor(self):
		supervisor_doc = frappe.db.get_list("Operations Shift",
			filters={'project': self.project},
			fields=['supervisor', 'supervisor_name'],
			limit=1
		)
		if supervisor_doc:
			self.supervisor = supervisor_doc[0].supervisor
			self.supervisor_name = supervisor_doc[0].supervisor_name

	def fill_items(self):
		current_date = getdate()
		last_day = get_last_day(current_date)
		first_day = get_first_day(current_date)
		contract = frappe.get_doc("Contracts", self.contract)
		for item in contract.items:
			if item.subitem_group == "Service":
				if item.rate_type == 'Monthly':
					if not item.no_of_days_off:
						item.no_of_days_off = 0
					else:
						item.no_of_days_off = int(item.no_of_days_off)
					roles = frappe.db.sql(f""" 
						SELECT name FROM `tabOperations Role` 
						WHERE sale_item="{item.item_code}" AND project="{self.project}" 
					""", as_dict=1)
					roles_dict = {}
					schedule_count = 0
					for role in roles:
						schedules = frappe.db.get_list(
							"Employee Schedule",
							filters={
								'date': ['BETWEEN', [first_day, last_day]],
								'project': self.project,
								'operations_role': ['in', role.name],
								'employee_availability': 'Working'
							}
						)
						roles_dict[role.name] = len(schedules)
						schedule_count += roles_dict[role.name]
					# check counts
					last_day = getdate(last_day)
					if item.rate_type_off == 'Full Month':
						expected = item.count*last_day.day
					elif item.rate_type_off == 'Days Off' and item.days_off_category == 'Monthly':
						expected = item.count* (last_day.day - item.no_of_days_off)
					elif item.rate_type_off == 'Days Off' and item.days_off_category == 'Weekly':
						week_range = get_week_start_end(str(getdate()))
						first_day = week_range.start
						last_day = week_range.end
						for role in roles:
							schedules = frappe.db.get_list(
								"Post Schedule",
								filters={
									'date': ['BETWEEN', [first_day, last_day]],
									'project': self.project,
									'operations_role': ['in', role.name],
									'post_status': 'Planned'
								}
							)
						roles_dict[role.name] = len(schedules)
						schedule_count += roles_dict[role.name]
						expected = item.count* (7 - item.no_of_days_off)

					# check counts
					created = schedule_count
					comment = ""
					if created == 0:
						comment = "No schedule created"
					if expected > created:
						comment = "Less schedule created"
					elif expected < created:
						comment = "More schedule created"

					if comment:
						self.append('items', {
							'item': item.item_code,
							'expected': expected,
							'scheduled': created,
							'from_date': first_day,
							'to_date': last_day,
							'comment': comment
						})

def schedule_roster_checker():
	for row in frappe.db.get_list("Contracts"):
		try:
			doc = frappe.get_doc({"doctype":"Post Scheduler Checker", 'contract': row.name}).insert(ignore_permissions=True)
		except Exception as e:
			print(e)
	frappe.db.commit()

@frappe.whitelist()
def generate_checker():
	frappe.enqueue(schedule_roster_checker)