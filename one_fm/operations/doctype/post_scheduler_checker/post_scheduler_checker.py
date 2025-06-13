# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe.utils import getdate, get_last_day, get_first_day, date_diff
from frappe.model.document import Document
from one_fm.utils import get_week_start_end
from one_fm.operations.doctype.operations_shift.operations_shift import get_supervisor_operations_shifts, get_shift_supervisor

class PostSchedulerChecker(Document):
	def autoname(self):
		self.name = f"{self.contract}-{str(getdate())}"
	def before_insert(self):
		name = f"{self.contract}-{str(getdate())}"
		if frappe.db.exists(self.doctype, {'name': name}):
			frappe.get_doc(self.doctype, name).delete()

	def validate(self):
		if self.is_new():
			self.fill_items()
			if not self.items:
				frappe.throw('No issues found.')
		if not self.check_date:
			self.check_date = getdate()
		self.__get_shift_supervisor()
		self.get_site_supervisor()


	def after_insert(self):
		# self.fill_items()
		# if not self.items:
		# 	frappe.throw('No issues found.')
		frappe.db.commit()

	def __get_shift_supervisor(self):
		shifts = get_supervisor_operations_shifts(project=self.project)
		if shifts and len(shifts) > 0:
			self.supervisor = get_shift_supervisor(shifts[0])
			if self.supervisor:
				self.supervisor_name = frappe.db.get_value("Employee", self.supervisor, "employee_name")


	def get_site_supervisor(self):
		try:
			site_supevisor_list = frappe.db.sql(f"""SELECT account_supervisor, account_supervisor_name from `tabOperations Site`
								 			WHERE project = '{self.project}'
											AND account_supervisor in (SELECT employee from `tabEmployee Schedule`
											WHERE employee_availability = 'Working'
											AND date = '{self.check_date}')""", as_dict=1)
			if site_supevisor_list:
				site = site_supevisor_list[0]
				self.site_supervisor, self.site_supervisor_name = site["account_supervisor"], site["account_supervisor_name"]

			if self.site_supervisor:
				self.site_supervisor_user = frappe.db.get_value("Employee", self.site_supervisor, "user_id")

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), str(e))



	def fill_items(self):
		current_date = getdate()
		last_day = getdate(get_last_day(current_date))
		first_day = getdate(get_first_day(current_date))
		week_range = get_week_start_end(str(getdate()))
		datediff = date_diff(last_day, first_day) + 1

		contract = frappe.get_doc("Contracts", self.contract)
		for item in contract.items:
			message = """"""
			expected = 0
			if not item.no_of_days_off:item.no_of_days_off = 0
			else:item.no_of_days_off=int(item.no_of_days_off)
			if item.subitem_group == "Service" and item.rate_type=='Monthly':
				roles = [i.name for i in frappe.db.sql(f"""
					SELECT name FROM `tabOperations Role`
					WHERE sale_item="{item.item_code}" AND project="{self.project}"
				""", as_dict=1)]
				roles_dict = {}
				schedule_count = 0
				operations_post = frappe.db.get_list(
					"Operations Post",
					filters={
						'project': self.project,
						'post_template': ['in', roles],
						"status": "Active"
					}
				)
				if not roles:
					message += f"""No operations roles created with sale item {item.item_code} in project {contract.project}, for contract {contract.name} in items row {item.idx}\n\n"""
				if not operations_post:
					message += f"""No operations posts created with sale item {item.item_code} in project {contract.project}, for contract {contract.name} in items row {item.idx}\n\n"""
				elif len(operations_post)>item.count:
					message += f"""More operations post created, expected: {item.count}, created: {len(operations_post)} for roles {roles}\n\n"""
				elif len(operations_post)<item.count:
					message += f"""Less operations post created, expected: {item.count}, created: {len(operations_post)} for roles {roles}\n\n"""

				# create final records
				if item.rate_type == 'Monthly':
					expected = 0
					no_of_days_off = 0
					if item.rate_type_off == 'Full Month':
						expected = getdate(get_last_day(getdate())).day
						no_of_days_off = 0
					elif item.rate_type_off == 'Days Off':
						if item.days_off_category == 'Monthly':
							expected = getdate(get_last_day(current_date)).day - item.no_of_days_off
							no_of_days_off = item.no_of_days_off
						elif item.days_off_category == 'Weekly':
							first_day = week_range.start
							last_day = week_range.end
							expected = 7 - item.no_of_days_off
							no_of_days_off = item.no_of_days_off
					for post in operations_post:
						post_schedules = get_post_schedules(project=contract.project, post=post, first_day=first_day, last_day=last_day)
						if not post_schedules:
							message += f"""No post schedules created for Post  ({post.name})\n\n"""
						elif post_schedules > expected:
							message += f"""More post schedules created, expected: {expected}, created: {post_schedules} for post {post.name}\n\n"""
						elif post_schedules < expected:
							message += f"""Less post schedules created, expected: {expected}, created: {post_schedules} for post {post.name}\n\n"""

					if message:
						self.append('items', {
							'item': item.item_code,
							'from_date': first_day,
							'to_date': last_day,
							'rate_type': item.rate_type,
							'rate_type_off': item.rate_type_off,
							'no_of_days_off': item.no_of_days_off,
							'days_off_category': item.days_off_category,
							'comment': message
						})
				else:
					self.append('items', {
							'item': item.item_code,
							'from_date': first_day,
							'to_date': last_day,
							'rate_type': item.rate_type,
							'rate_type_off': '',
							'no_of_days_off': 0,
							'comment': "Hourly rate_type."
						})
			last_day = getdate(get_last_day(current_date))
			first_day = getdate(get_first_day(current_date))

def schedule_roster_checker():
	contracts = frappe.db.sql(""" SELECT c.name from `tabContracts` c JOIN `tabProject` p ON p.name = c.project WHERE c.workflow_state = 'Active'
						   		  AND p.is_active = 'Yes' """, as_dict=1)
	if not contracts:
		return

	for row in [obj.get("name") for obj in contracts]:
		try:
			doc = frappe.get_doc({"doctype":"Post Scheduler Checker", 'contract': row}).insert(ignore_permissions=True)
		except Exception as e:
			print(e)
	frappe.db.commit()

def get_post_schedules(project, post, first_day, last_day):
	return frappe.db.count(
		"Post Schedule",
		filters={
			"date": ['BETWEEN', [first_day, last_day]],
			"project": project,
			"post": post.name,
			"post_status": 'Planned'
		}
	)

@frappe.whitelist()
def generate_checker():
	count = frappe.db. sql("""
			SELECT
				COUNT (*)
			FROM
				`tabContracts` c JOIN `tabProject` p ON p.name = c.project
			WHERE
				c.workflow_state = 'Active' AND p.is_active = 'Yes'
	""") [0] (0)

	if count:
		page = 1
		page_size = 10
		iterations = math.ceil (count / page_size)
		for page in range(page, iterations):
			offset = (page - 1) * page_size
			frappe.enqueue(create_post_schedule_checker_from_contracts, page=page, offset=offset)

def create_post_schedule_checker_from_contracts(page, offset):
	contracts = frappe.db.sql("""
		SELECT
			c.name
		FROM
			`tabContracts` c JOIN `tabProject` p ON p.name = c.project
		WHERE
			c.workflow_state = 'Active' AND p.is_active = 'Yes'
		LIMIT %s OFFSET %s
	""", (page_size, offset), as_dict=1)

	if not contracts:
		return

	for row in [obj.get("name") for obj in contracts]:
		try:
			doc = frappe.get_doc({"doctype":"Post Scheduler Checker", 'contract': row}).insert(ignore_permissions=True)
		except Exception as e:
			print(e)
	frappe.db.commit()
