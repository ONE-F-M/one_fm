# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe
from frappe.utils import getdate, get_last_day, get_first_day, date_diff, add_days, add_months, nowdate
from frappe.model.document import Document
from one_fm.utils import get_week_start_end
from one_fm.operations.doctype.operations_shift.operations_shift import get_supervisor_operations_shifts, get_shift_supervisor
import math

class PostSchedulerChecker(Document):
	pass

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

def get_working_site_supervisor(project, date):
	try:
		site_supevisor_list = frappe.db.sql(f"""SELECT account_supervisor from `tabOperations Site`
							 			WHERE project = '{project}'
										AND account_supervisor in (SELECT employee from `tabEmployee Schedule`
										WHERE employee_availability = 'Working'
										AND date = '{date}')""", as_dict=1)
		if site_supevisor_list:
			site = site_supevisor_list[0]
			return site["account_supervisor"]
			
		return None

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), str(e))

	
def get_post_scheduler_items(contract, project):
	current_date = getdate()
	contract = frappe.get_doc("Contracts", contract)

	items = []

	for item in contract.items:

		item_message = ""

		if not item.no_of_days_off: item.no_of_days_off = 0
		else: item.no_of_days_off=int(item.no_of_days_off)

		if item.subitem_group == "Service" and item.rate_type=='Monthly':
			roles = [i.name for i in frappe.db.sql(f"""
				SELECT name FROM `tabOperations Role`
				WHERE sale_item="{item.item_code}" AND project="{project}"
			""", as_dict=1)]

			operations_post = frappe.db.get_list(
				"Operations Post",
				filters={
					'project': project,
					'post_template': ['in', roles],
					"status": "Active"
				},
				fields=["name", "start_date", "end_date"]
			)
			if not roles:
				item_message += f"""No operations roles created with sale item {item.item_code} in project {contract.project}, for contract {contract.name} in items row {item.idx}\n\n"""
			if not operations_post:
				item_message += f"""No operations posts created with sale item {item.item_code} in project {contract.project}, for contract {contract.name} in items row {item.idx}\n\n"""
			elif len(operations_post)>item.count:
				item_message += f"""More operations post created, expected: {item.count}, created: {len(operations_post)} for roles {roles}\n\n"""
			elif len(operations_post)<item.count:
				item_message += f"""Less operations post created, expected: {item.count}, created: {len(operations_post)} for roles {roles}\n\n"""

			for post in operations_post:
				# Get two periods: current & next
				periods = []

				if item.rate_type_off == 'Days Off' and item.days_off_category == 'Weekly':
					# Weekly: current week and next week
					curr_week = get_week_start_end(str(current_date))
					next_week = get_week_start_end(str(add_days(current_date, 7)))
					periods.append((curr_week.start, curr_week.end))
					periods.append((next_week.start, next_week.end))
				else:
					# Monthly: current month and next month
					curr_month_start = get_first_day(current_date)
					curr_month_end = get_last_day(current_date)
					next_month_start = get_first_day(add_months(current_date, 1))
					next_month_end = get_last_day(add_months(current_date, 1))
					periods.append((curr_month_start, curr_month_end))
					periods.append((next_month_start, next_month_end))

				for period_start, period_end in periods:
					first_day = getdate(period_start)
					last_day = getdate(period_end)

					# Check if post's start and end dates are within the period
					if post.start_date and post.start_date > last_day:
						continue
					if post.end_date and post.end_date < first_day:
						continue

					if post.start_date and post.start_date > first_day:
						first_day = getdate(post.start_date)
					if post.end_date and post.end_date < last_day:
						last_day = getdate(post.end_date)

					expected = date_diff(last_day, first_day) + 1

					if item.rate_type_off == 'Days Off':
						expected -= item.no_of_days_off

					post_schedules = get_post_schedules(
						project=contract.project,
						post=post,
						first_day=first_day,
						last_day=last_day
					)

					post_message = ""
					if not post_schedules:
						post_message += f"""No post schedules created for Post ({post.name}) from {first_day} to {last_day}\n\n"""
					elif post_schedules > expected:
						post_message += f"""More post schedules created from {first_day} to {last_day}, expected: {expected}, created: {post_schedules} for post {post.name}\n\n"""
					elif post_schedules < expected:
						post_message += f"""Less post schedules created from {first_day} to {last_day}, expected: {expected}, created: {post_schedules} for post {post.name}\n\n"""

					if post_message:
						items.append({
							'item': item.item_code,
							'from_date': first_day,
							'to_date': last_day,
							'rate_type': item.rate_type,
							'rate_type_off': item.rate_type_off,
							'no_of_days_off': item.no_of_days_off,
							'days_off_category': item.days_off_category,
							'comment': item_message + post_message
						})

	return items

def schedule_roster_checker():
	contracts = frappe.db.sql("""SELECT c.name, p.name as project from `tabContracts` c JOIN `tabProject` p ON p.name = c.project WHERE c.workflow_state = 'Active'
						   		  AND p.is_active = 'Yes' """, as_dict=1)
	if not contracts:
		return

	for obj in contracts:
		try:
			today = getdate()

			contract = obj.get('name')
			project = obj.get('project')

			items = get_post_scheduler_items(contract, project)

			if len(items) > 0:
				yesterday_repeat_count = frappe.db.get_value(
					"Post Scheduler Checker",
					{
						"project": project,
						"check_date": add_days(today, -1),
						"creation": ["between", [add_days(nowdate(), -1), nowdate()]],
					},
					["repeat_count"]
				)

				# Delete exising for target contract against date
				frappe.delete_doc_if_exists("Post Scheduler Checker", f"{project}-{str(today)}")

				post_scheduler_checker = frappe.new_doc("Post Scheduler Checker")

				post_scheduler_checker.check_date = today
				post_scheduler_checker.repeat_count = (yesterday_repeat_count or 0) + 1
				post_scheduler_checker.contract = contract
				post_scheduler_checker.project = project
				post_scheduler_checker.site_supervisor = get_working_site_supervisor(project, today)
				post_scheduler_checker.project_manager = frappe.db.get_value('Project', project, 'account_manager')

				for sub_item in items:
					post_scheduler_checker.append("items", sub_item)

				post_scheduler_checker.save()
			
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error while generating Post Scheduler Checker")
			continue

	frappe.db.commit()

@frappe.whitelist()
def generate_checker():
	count = frappe.db. sql("""
			SELECT
				COUNT(*)
			FROM
				`tabContracts` c JOIN `tabProject` p ON p.name = c.project
			WHERE
				c.workflow_state = 'Active' AND p.is_active = 'Yes'
	""")[0][0]

	if count == 0:
		return
	
	page = 1
	page_size = 10
	iterations = math.ceil (count / page_size)
	for current_page in range(page, iterations + 1):
		offset = (current_page - 1) * page_size
		frappe.enqueue(create_post_schedule_checker_from_contracts, page_size=page_size, offset=offset)

def create_post_schedule_checker_from_contracts(page_size, offset):
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
