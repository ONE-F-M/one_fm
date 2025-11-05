# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt
import calendar

import frappe
from frappe.model.document import Document
from frappe.utils import (getdate, get_first_day, get_last_day, add_days, add_months, date_diff, get_datetime)
from one_fm.utils import get_week_start_end


class ContractComplianceChecker(Document):
	pass



class GenerateContractComplianceChecker:
	
	def __init__(self):
		self.yesterday = getdate(frappe.utils.add_days(frappe.utils.today(), -1))
		self.day_before_yesterday = getdate(frappe.utils.add_days(frappe.utils.today(), -2))
		self.today = getdate(frappe.utils.today())

	def get_contract_items_list(self):
		return frappe.db.sql("""
			SELECT ci.idx, ci.parent, ci.count, ci.item_code, ci.days_off_category, ci.no_of_days_off, ci.off_type, ci.service_type, c.project
			FROM `tabContract Item` ci
			INNER JOIN `tabContracts` c ON ci.parent = c.name
			AND c.workflow_state = %s
		""", ("Active"), as_dict=1)
	
	def get_operation_roles(self, sale_item, project):
		return frappe.db.get_list('Operations Role', {'sale_item': sale_item, 'status': 'Active', "project": project}, pluck='name')
	
	def get_operation_posts(self, operation_roles, project):
		return frappe.db.get_list(
				"Operations Post",
				filters={
					'project': project,
					'post_template': ['in', operation_roles],
					"status": "Active"
				},
				fields=["name", "start_date", "end_date"]
			)
	
	def get_post_schedules(self, project, post, start_date, end_date):
		return frappe.db.count(
			"Post Schedule",
			filters={
				"date": ['BETWEEN', [start_date, end_date]],
				"project": project,
				"post": post.name,
				"post_status": 'Planned'
			}
		)
	
	def get_total_employee_schedule_count(self, operations_roles, start_date, end_date):
		if not operations_roles:
			return 0
		
		if self.day_before_yesterday >= start_date:
			attendance_count = frappe.db.count('Attendance', {
				'roster_type': "Basic",
				"status": "Present",
				"attendance_date": ["between", [start_date, self.day_before_yesterday]],
				"operations_role": ["in", operations_roles]
			})
		else:
			attendance_count = 0
			
		if self.yesterday <= end_date:
			schedule_count = frappe.db.count('Employee Schedule', {
				'roster_type': "Basic",
				"employee_availability": "Working",
				"date": ["between", [self.yesterday, end_date]],
				"operations_role": ["in", operations_roles]
			})
		else:
			schedule_count = 0

		return attendance_count + schedule_count
	
	def calculate_manpower_full_month_compliance(self, contract_data, start_date, end_date):
		start_date = getdate(start_date)
		end_date = getdate(end_date)

		comment = ""
		
		operations_roles = self.get_operation_roles(contract_data.item_code, contract_data.project)

		# No operations role created
		if not operations_roles:
			comment += f"No operations roles created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"

		operation_posts = self.get_operation_posts(operations_roles, contract_data.project)

		total_operations_post = len(operation_posts)

		if total_operations_post == 0:
			comment += f"No operations posts created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"		
		elif total_operations_post < contract_data.count:
			comment += f"Less operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"
		elif total_operations_post > contract_data.count:
			comment += f"More operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"

		for post in operation_posts:
			# Scope start_date and end_date per post
			post_start_date = start_date
			post_end_date = end_date

			# Check if post's start and end dates are within the period
			if post.start_date and getdate(post.start_date) > post_end_date:
				continue
			if post.end_date and getdate(post.end_date) < post_start_date:
				continue
			if post.start_date and getdate(post.start_date) > post_start_date:
				post_start_date = getdate(post.start_date)
			if post.end_date and getdate(post.end_date) < post_end_date:
				post_end_date = getdate(post.end_date)

			expected_post_schedules = date_diff(post_end_date, post_start_date) + 1
			post_schedules_count = self.get_post_schedules(
					project=contract_data.project,
					post=post,
					start_date=post_start_date,
					end_date=post_end_date
				)
				
			if not post_schedules_count:
				comment += f"""No post schedules created for Post ({post.name}) from {post_start_date} to {post_end_date}\n\n"""
			elif post_schedules_count > expected_post_schedules:
				comment += f"""More post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""
			elif post_schedules_count < expected_post_schedules:
				comment += f"""Less post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""

		if comment:
			return True, {
				"contract": contract_data.parent,
				"sale_item": contract_data.item_code,
				"from_date": start_date,
				"to_date": end_date,
				"comment": comment
			}
		
		return False, {}
	
	def calculate_post_schedule_full_month_compliance(self, contract_data, start_date, end_date):
		start_date = getdate(start_date)
		end_date = getdate(end_date)

		comment = ""
		
		operations_roles = self.get_operation_roles(contract_data.item_code, contract_data.project)

		# No operations role created
		if not operations_roles:
			comment += f"No operations roles created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"

		operation_posts = self.get_operation_posts(operations_roles, contract_data.project)

		total_operations_post = len(operation_posts)

		if total_operations_post == 0:
			comment += f"No operations posts created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"		
		elif total_operations_post < contract_data.count:
			comment += f"Less operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"
		elif total_operations_post > contract_data.count:
			comment += f"More operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"

		for post in operation_posts:
			# Scope start_date and end_date per post
			post_start_date = start_date
			post_end_date = end_date

			# Check if post's start and end dates are within the period
			if post.start_date and post.start_date > post_end_date:
				continue
			if post.end_date and post.end_date < post_start_date:
				continue
			if post.start_date and post.start_date > post_start_date:
				post_start_date = getdate(post.start_date)
			if post.end_date and post.end_date < post_end_date:
				post_end_date = getdate(post.end_date)

			expected_post_schedules = date_diff(post_end_date, post_start_date) + 1
			post_schedules_count = self.get_post_schedules(
					project=contract_data.project,
					post=post,
					start_date=post_start_date,
					end_date=post_end_date
				)
				
			if not post_schedules_count:
				comment += f"""No post schedules created for Post ({post.name}) from {post_start_date} to {post_end_date}\n\n"""
			elif post_schedules_count > expected_post_schedules:
				comment += f"""More post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""
			elif post_schedules_count < expected_post_schedules:
				comment += f"""Less post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""

		if comment:
			return True, {
				"contract": contract_data.parent,
				"sale_item": contract_data.item_code,
				"from_date": start_date,
				"to_date": end_date,
				"comment": comment
			}
		
		return False, {}
	
	def calculate_manpower_day_off_compliance(self, contract_data, start_date, end_date):
		start_date = getdate(start_date)
		end_date = getdate(end_date)

		comment = ""

		operations_roles = self.get_operation_roles(contract_data.item_code, contract_data.project)

		# No operations role created
		if not operations_roles:
			comment += f"No operations roles created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"

		working_days_in_period = (date_diff(end_date, start_date) + 1) - contract_data.no_of_days_off
		expected_schedule_count = working_days_in_period * contract_data.count

		actual_schedule_count = self.get_total_employee_schedule_count(operations_roles, start_date, end_date)

		if actual_schedule_count > expected_schedule_count:
			comment += f"More employee schedules created from {start_date} to {end_date}, expected {expected_schedule_count}, created {actual_schedule_count} for roles {operations_roles} against contract {contract_data.parent} in items row {contract_data.idx}\n\n"
		elif actual_schedule_count < expected_schedule_count:
			comment += f"Less employee schedules created from {start_date} to {end_date}, expected {expected_schedule_count}, created {actual_schedule_count} for roles {operations_roles} against contract {contract_data.parent} in items row {contract_data.idx}\n\n"

		if actual_schedule_count != expected_schedule_count:
			return True, {
				'from_date': start_date,
				'to_date': end_date,
				'comment': comment,
				'contract': contract_data.parent,
				'sale_item': contract_data.item_code,
			}
		return False, {}
	
	def calculate_post_schedule_day_off_compliance(self, contract_data, start_date, end_date):
		start_date = getdate(start_date)
		end_date = getdate(end_date)

		comment = ""

		operations_roles = self.get_operation_roles(contract_data.item_code, contract_data.project)

		# No operations role created
		if not operations_roles:
			comment += f"No operations roles created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"

		operation_posts = self.get_operation_posts(operations_roles, contract_data.project)

		total_operations_post = len(operation_posts)

		if total_operations_post == 0:
			comment += f"No operations posts created with sale item {contract_data.item_code} in project {contract_data.project}, for contract {contract_data.parent} in items row {contract_data.idx}\n\n"		
		elif total_operations_post < contract_data.count:
			comment += f"Less operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"
		elif total_operations_post > contract_data.count:
			comment += f"More operations post created, expected: {contract_data.count}, created: {total_operations_post} for roles {operations_roles}\n\n"
		
		for post in operation_posts:
			# Scope start_date and end_date per post
			post_start_date = start_date
			post_end_date = end_date

			# Check if post's start and end dates are within the period
			if post.start_date and getdate(post.start_date) > post_end_date:
				continue
			if post.end_date and getdate(post.end_date) < post_start_date:
				continue
			if post.start_date and getdate(post.start_date) > post_start_date:
				post_start_date = getdate(post.start_date)
			if post.end_date and getdate(post.end_date) < post_end_date:
				post_end_date = getdate(post.end_date)

			working_days_in_period = (date_diff(post_end_date, post_start_date) + 1)
			expected_post_schedules = working_days_in_period - contract_data.no_of_days_off

			post_schedules_count = self.get_post_schedules(
					project=contract_data.project,
					post=post,
					start_date=post_start_date,
					end_date=post_end_date
				)
				
			if not post_schedules_count:
				comment += f"""No post schedules created for Post ({post.name}) from {post_start_date} to {post_end_date}\n\n"""
			elif post_schedules_count > expected_post_schedules:
				comment += f"""More post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""
			elif post_schedules_count < expected_post_schedules:
				comment += f"""Less post schedules created from {post_start_date} to {post_end_date}, expected: {expected_post_schedules}, created: {post_schedules_count} for post {post.name}\n\n"""
		
		if comment:
			return True, {
				"contract": contract_data.parent,
				"sale_item": contract_data.item_code,
				"from_date": start_date,
				"to_date": end_date,
				"comment": comment
			}
		
		return False, {}
	
	@staticmethod
	def get_diff_comment(expected_total, actual_total):
		diff = actual_total - expected_total
		if diff >= 1:
			return f"More Schedules Created, expected {expected_total}, created {actual_total}"
		elif diff <= -1:
			return f"Less Schedules Created, expected {expected_total}, created {actual_total}"
		return ""
	
	@staticmethod
	def get_duration_periods(is_weekly):
		current_date = getdate(frappe.utils.today())
		periods = []

		if is_weekly:
			curr_week = get_week_start_end(str(current_date))
			next_week = get_week_start_end(str(add_days(current_date, 7)))
			periods.append((curr_week.start, curr_week.end))
			periods.append((next_week.start, next_week.end))
		else:
			curr_month_start = get_first_day(current_date)
			curr_month_end = get_last_day(current_date)
			next_month_start = get_first_day(add_months(current_date, 1))
			next_month_end = get_last_day(add_months(current_date, 1))
			periods.append((curr_month_start, curr_month_end))
			periods.append((next_month_start, next_month_end))

		return periods
	
	def create_compliance_checker(self, contract, compliance_details):
		contract_details = frappe.db.get_value("Contracts", contract, 
			["client", "project", "project.account_manager"], as_dict=1)
		
		yesterday_repeat_count = frappe.db.get_value("Contract Compliance Checker", {
				"project": contract_details.project,
				"check_date": add_days(getdate(), -1),
				"creation": ["between", [get_datetime(str(add_days(getdate(), -1)) + " 00:00:00"), get_datetime(str(add_days(getdate(), -1)) + " 23:59:59")]],
			},
			["repeat_count"]
		)
		
		existing_doc = frappe.db.exists("Contract Compliance Checker", { "project": contract_details.project, "check_date": self.today })

		if existing_doc:
			frappe.delete_doc("Contract Compliance Checker", existing_doc, force=True)
		
		doc = frappe.get_doc({
			"doctype": "Contract Compliance Checker",
			"project": contract_details.project,
			"contract": contract,
			"project_manager": contract_details.account_manager,
			"repeat_count": (yesterday_repeat_count or 0) + 1,
			"check_date": self.today,
			"client": contract_details.client,
		})
		
		for detail in compliance_details:
			doc.append("items", {
				"item": detail.get("sale_item"),
				"from_date": detail.get("from_date"),
				"to_date": detail.get("to_date"),
				"comment": detail.get("comment")
			})
		
		doc.insert(ignore_permissions=True)
	
	def execute(self):
		contract_items_list = self.get_contract_items_list()

		results = []
		
		for contract_item in contract_items_list:
			try:
				is_off_type_full_month = contract_item.off_type == "Full Month"
				has_days_off = contract_item.off_type == "Days Off"
				has_weekly_days_off = contract_item.days_off_category == "Weekly"

				duration_periods = self.get_duration_periods(is_weekly=has_days_off and has_weekly_days_off)

				for period_start, period_end in duration_periods:
					if contract_item.service_type == "Manpower":
						status, data = self.calculate_manpower_full_month_compliance(contract_item, period_start, period_end) if is_off_type_full_month else self.calculate_manpower_day_off_compliance(contract_item, period_start, period_end)
					elif contract_item.service_type == "Post Schedule":
						status, data = self.calculate_post_schedule_full_month_compliance(contract_item, period_start, period_end) if is_off_type_full_month else self.calculate_post_schedule_day_off_compliance(contract_item, period_start, period_end)
					else:
						continue

					if status:
						results.append(data)

			except Exception as e:
				frappe.log_error(title="Contract Compliance Checker Execution",message=frappe.get_traceback())
				pass
		
		contract_groups = {}
		for item in results:
			contract = item['contract']
			if contract not in contract_groups:
				contract_groups[contract] = []
			contract_groups[contract].append(item)
		
		for contract, compliance_details in contract_groups.items():
			self.create_compliance_checker(contract, compliance_details)


def generate_contract_compliance_checker():
	try:
		generator = GenerateContractComplianceChecker()
		generator.execute()
	except Exception as e:
		frappe.log_error(title="Contract Compliance Checker Generation Failed", message=frappe.get_traceback())
		pass