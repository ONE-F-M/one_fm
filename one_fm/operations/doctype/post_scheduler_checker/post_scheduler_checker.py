# Copyright (c) 2022, ONE FM and contributors
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

def get_post_active_windows(post):
	"""Return all validated "Active" windows for a post as (start, end) date tuples:
	the current main window plus every historical window archived in the
	Operations Post Activation child table. ``None`` means an open bound."""
	windows = []

	main_start = getdate(post.start_date) if post.get("start_date") else None
	main_end = getdate(post.end_date) if post.get("end_date") else None
	if main_start or main_end:
		windows.append((main_start, main_end))

	history = frappe.get_all(
		"Operations Post Activation",
		filters={"parent": post.name, "parenttype": "Operations Post"},
		fields=["operations_post_start_date", "operations_post_end_date"]
	)
	for row in history:
		hist_start = getdate(row.operations_post_start_date) if row.operations_post_start_date else None
		hist_end = getdate(row.operations_post_end_date) if row.operations_post_end_date else None
		if hist_start or hist_end:
			windows.append((hist_start, hist_end))

	return windows

def get_active_intervals_in_period(windows, period_start, period_end):
	"""Clip each active window to [period_start, period_end] and merge overlapping/
	adjacent intervals so overlapping windows are not double counted."""
	clipped = []
	for win_start, win_end in windows:
		start = period_start if (win_start is None or win_start < period_start) else win_start
		end = period_end if (win_end is None or win_end > period_end) else win_end
		if start <= end:
			clipped.append((start, end))

	clipped.sort()
	merged = []
	for start, end in clipped:
		if merged and start <= add_days(merged[-1][1], 1):
			merged[-1] = (merged[-1][0], max(merged[-1][1], end))
		else:
			merged.append((start, end))

	return merged

def get_post_schedules(project, post, first_day, last_day, include_client_post_off=False):
	filters = {
		"date": ['BETWEEN', [first_day, last_day]],
		"project": project,
		"post": post.name
	}

	if include_client_post_off:
		filters["post_status"] = ['in', ['Planned', 'Client Post Off']]
	else:
		filters["post_status"] = 'Planned'

	return frappe.db.count("Post Schedule", filters=filters)

def get_working_site_supervisor(project, date):
	try:
		site_supevisor_list = frappe.db.sql(f"""SELECT site_supervisor from `tabOperations Site`
							 			WHERE project = '{project}'
										AND site_supervisor in (SELECT employee from `tabEmployee Schedule`
										WHERE employee_availability = 'Working'
										AND date = '{date}')""", as_dict=1)
		if site_supevisor_list:
			site = site_supevisor_list[0]
			return site["site_supervisor"]
			
		return None

	except Exception as e:
		frappe.log_error(message=str(e), title="Error fetching working site supervisor")

	
def get_post_scheduler_items(contract, project):
	current_date = getdate()
	contract = frappe.get_doc("Contracts", contract)

	items = []

	for item in contract.contract_items_operation:
		# Skip items of type "Items" as they don't require post scheduling validation
		if item.is_daily_operation_handled_by_us == "No":
			continue

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
				# AC4: validate against all active windows (current main window + history)
				active_windows = get_post_active_windows(post)

				# Get two periods: current & next
				periods = []

				if item.off_type == 'Days Off' and item.days_off_category == 'Weekly':
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
					period_start = getdate(period_start)
					period_end = getdate(period_end)

					# AC4: intersect the period with every active window (main + history).
					# The post is only expected to have schedules within these windows.
					active_intervals = get_active_intervals_in_period(
						active_windows, period_start, period_end
					)
					if not active_intervals:
						# Post was not active at all during this period.
						continue

					first_day = active_intervals[0][0]
					last_day = active_intervals[-1][1]

					include_client_post_off = False
					if item.off_type == 'Full Month':
						include_client_post_off = True
					elif item.off_type == 'Days Off' and item.days_off_category in ['Monthly', 'Weekly']:
						include_client_post_off = True

					# Expected days and actual schedules are summed across the (disjoint)
					# active intervals, so overlapping windows are never double counted.
					expected = sum(date_diff(end, start) + 1 for start, end in active_intervals)

					if item.off_type == 'Days Off':
						expected -= item.no_of_days_off

					post_schedules = sum(
						get_post_schedules(
							project=contract.project,
							post=post,
							first_day=start,
							last_day=end,
							include_client_post_off=include_client_post_off
						)
						for start, end in active_intervals
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
							'off_type': item.off_type,
							'no_of_days_off': item.no_of_days_off,
							'days_off_category': item.days_off_category,
							'comment': item_message + post_message
						})

	return items

def schedule_roster_checker(projects=None):
	"""Rebuild today's Post Scheduler Checker for every active contract, or just some.

	WI-002018: `projects` narrows it to the projects whose roster has just changed, so a
	staffing gap opened by a cleanup is reported the moment it appears rather than waiting
	for tomorrow's scheduled run. Left empty it behaves exactly as the scheduled job always
	has, which is how it is still called from the scheduler.
	"""
	conditions = ""
	values = {}
	if projects:
		conditions = " AND p.name IN %(projects)s"
		values["projects"] = tuple(projects)

	contracts = frappe.db.sql("""SELECT c.name, p.name as project from `tabContracts` c JOIN `tabProject` p ON p.name = c.project WHERE c.workflow_state = 'Active'
						   		  AND p.is_active = 'Yes' """ + conditions, values, as_dict=1)
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
				post_scheduler_checker.project_manager = frappe.db.get_value('Project', project, 'project_manager')

				for sub_item in items:
					post_scheduler_checker.append("items", sub_item)

				post_scheduler_checker.save()
			
		except Exception as e:
			frappe.log_error(title="Error while generating Post Scheduler Checker", message=frappe.get_traceback())
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
