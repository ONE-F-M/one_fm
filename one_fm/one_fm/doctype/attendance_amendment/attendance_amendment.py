# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Extract
from frappe.utils import cint, cstr
from calendar import monthrange
from frappe import _

class AttendanceAmendment(Document):
	def validate(self):
		self.recalculate_working_days()

	def recalculate_working_days(self):
		for row in self.get("attendance_details") + self.get("overtime_details"):
			working_days = 0
			off_days = 0
			# OT + Attendance Status stores statuses in day_X; OT + hours modes use day_X_hour
			use_hours = self.attendance_based_on in ("Shift Hours", "Working Hours")

			for i in range(1, 32):
				if use_hours:
					val = row.get(f"day_{i}")
					hour_val = row.get(f"day_{i}_hour")
					if isinstance(val, str) and val in ("Day Off", "Client Day Off"):
						off_days += 1
					elif hour_val and hour_val not in ("N/A",):
						try:
							if float(hour_val) > 0:
								working_days += 1
						except (ValueError, TypeError):
							pass
				else:
					# Attendance Status mode (basic rows only)
					val = row.get(f"day_{i}")
					if val in ["Present", "Working", "Work From Home"]:
						working_days += 1
					elif val == "Half Day":
						working_days += 0.5
					elif val in ["Day Off", "Client Day Off"]:
						off_days += 1
			row.working_days = working_days
			row.off_days = off_days

	@frappe.whitelist()
	def fetch_attendance_record(self):
		filters = self.get_attendance_amendment_filters()
		employee_details = get_employee_details()
		attendance_map = get_attendance_map(filters, self.attendance_based_on)
		data = get_rows(employee_details, filters, attendance_map, self.attendance_based_on)
		if data:
			self.update_attendance_records(data)
		else:
			frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")

		if self.ot_data_required:
			ot_attendance_map = get_ot_attendance_map(filters, self.attendance_based_on)
			ot_data = get_ot_rows(employee_details, filters, ot_attendance_map, self.attendance_based_on)
			if ot_data:
				self.update_attendance_records(ot_data, type="Overtime")
			else:
				frappe.msgprint(_("No OT attendance records found."), alert=True, indicator="orange")

	def get_attendance_amendment_filters(self):
		month_map = { 
			"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
			"July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
			"December": 12
		}
		filters = {
			"month": month_map.get(self.month),
			"year": self.year
		}
		if self.project:
			filters["project"] = self.project
		if self.site:
			filters["site"] = self.site
		return frappe._dict(filters)

	def update_attendance_records(self, data, type="Basic"):
		if not self.attendance_based_on:
			return
		child_table = "overtime_details" if type == "Overtime" else "attendance_details"
		self.set(child_table, [])

		# Non-numeric values that are statuses, not hours
		status_strings = {"Day Off", "Client Day Off", "Absent", "On Leave", "On Hold",
			"Present", "Half Day", "Work From Home", "Holiday",
			"Fingerprint Appointment", "Medical Appointment", "Working", "N/A"}

		for record in data:
			# Hours mode: Shift Hours / Working Hours → split into day_X (status) + day_X_hour (number)
			# Status mode: Attendance Status → store everything in day_X
			use_hours = self.attendance_based_on in ("Shift Hours", "Working Hours")

			if use_hours:
				day_fields = {}
				for i in range(1, 32):
					val = record.get(str(i), "N/A" if type == "Overtime" else "")
					if isinstance(val, str) and val in status_strings:
						day_fields[f"day_{i}"] = val
					else:
						day_fields[f"day_{i}_hour"] = val
			else:
				day_fields = {f"day_{i}": record.get(str(i), '') for i in range(1, 32)}

			self.append(child_table, {
				"employee": record.get("employee"),
				"employee_id": record.get("employee_id"),
				"employee_name": record.get("employee_name"),
				"sale_item": record.get("sale_item"),
				"shift": record.get("shift"),
				"working_days": record.get("working_days"),
				"off_days": record.get("off_days"),
				**day_fields
			})

def get_employee_details():
	Employee = frappe.qb.DocType("Employee")
	OperationsRole = frappe.qb.DocType("Operations Role")
	query = (
		frappe.qb.from_(Employee)
		.left_join(OperationsRole)
		.on(Employee.custom_operations_role_allocation == OperationsRole.name)
		.select(
			Employee.name,
			Employee.employee_id,
			Employee.employee_name,
			OperationsRole.sale_item
		)
		.where(Employee.shift_working == 1)
	)

	employee_details = query.run(as_dict=True)

	emp_map = {}

	for emp in employee_details:
		emp_map[emp.name] = emp

	return emp_map

def get_attendance_map(filters, attendance_based_on=None):
	"""Returns a dictionary of employee wise attendance map as per shifts for all the days of the month like
	{
		'employee1': {
				'Morning': {1: 'Present', 2: 'Absent', ...}
				'Evening': {1: 'Absent', 2: 'Present', ...}
		},
		'employee2': {
				'Afternoon': {1: 'Present', 2: 'Absent', ...}
				'Night': {1: 'Absent', 2: 'Absent', ...}
		},
		'employee3': {
				None: {1: 'On Leave'}
		}
	}
	"""
	non_day_off_attendance_records = get_non_day_off_attendance_records(filters)

	attendance_map = {}
	leave_map = {}

	for d in non_day_off_attendance_records:
		if d.status == "On Leave":
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append(d.day_of_month)
			continue

		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		if attendance_based_on == "Attendance Status":
			attendance_map[d.employee][d.shift][d.day_of_month] = d.status
		elif attendance_based_on == "Shift Hours":
			attendance_map[d.employee][d.shift][d.day_of_month] = d.shift_duration
		else:
			# Working Hours — use actual working hours from Attendance
			attendance_map[d.employee][d.shift][d.day_of_month] = d.working_hours

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_shift, days in leave_days.items():
			# no attendance records exist except leaves
			if employee not in attendance_map:
				attendance_map.setdefault(employee, {}).setdefault(assigned_shift, {})

			for day in days:
				for shift in attendance_map[employee].keys():
					attendance_map[employee][shift][day] = "On Leave"

	return attendance_map

def get_non_day_off_attendance_records(filters):
	from frappe.utils import get_last_day
	start_date = f"{filters.year}-{int(filters.month):02d}-01"
	end_date = get_last_day(start_date)

	Attendance = frappe.qb.DocType("Attendance")
	OperationsShift = frappe.qb.DocType("Operations Shift")
	ShiftType = frappe.qb.DocType("Shift Type")

	query = (
		frappe.qb.from_(Attendance)
		.join(OperationsShift)
		.on(Attendance.operations_shift == OperationsShift.name)
		.left_join(ShiftType)
		.on(OperationsShift.shift_type == ShiftType.name)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			OperationsShift.shift_classification.as_("shift"),
			Attendance.working_hours,
			ShiftType.duration.as_("shift_duration")
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.attendance_date >= start_date)
			& (Attendance.attendance_date <= end_date)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == "Basic")
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	return query.run(as_dict=True)

def get_rows(employee_details, filters, attendance_map, attendance_based_on):
	records = []

	day_off_attendance_map = get_day_off_attendance_map(filters)

	for employee, details in employee_details.items():
		employee_attendance = attendance_map.get(employee)

		employee_day_off_attendance = day_off_attendance_map.get(employee, {})

		if not employee_attendance:
			# no attendance records found for employee
			continue

		attendance_for_employee = get_attendance_status(filters, employee_attendance, employee_day_off_attendance, attendance_based_on)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee": details.name,
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"sale_item": details.sale_item
			})

		records.extend(attendance_for_employee)

	return records

def get_day_off_attendance_map(filters, roster_type="Basic"):
	from frappe.utils import get_last_day
	start_date = f"{filters.year}-{int(filters.month):02d}-01"
	end_date = get_last_day(start_date)

	Attendance = frappe.qb.DocType("Attendance")

	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			Attendance.working_hours
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.attendance_date >= start_date)
			& (Attendance.attendance_date <= end_date)
			& (Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == roster_type)
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	day_off_records = query.run(as_dict=True)

	day_off_map = {}

	for record in day_off_records:
		day_off_map.setdefault(record.employee, {})[record.day_of_month] = record.status
		
	return day_off_map

def get_attendance_status(filters, employee_non_day_off_attendance, employee_day_off_attendance=None, attendance_based_on=None):
	"""Returns list of shift-wise attendance status for employee
	[
			{'shift': 'Morning', 1: 'A', 2: 'P', 3: 'A'....},
			{'shift': 'Evening', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = monthrange(cint(filters.year), cint(filters.month))[1]
	attendance_values = []

	employee_non_day_off_attendance = employee_non_day_off_attendance or {}

	shifts = set(employee_non_day_off_attendance.keys())

	for shift in shifts:
		row = {"shift": shift}

		# Merge Attendance and Schedule statuses
		attendance_dict = { **employee_non_day_off_attendance.get(shift, {})}

		working_days = 0
		off_days = 0

		for day in range(1, total_days + 1):
			status = attendance_dict.get(day)

			# if status is not found in non day attendance records, check day off attendance
			if attendance_based_on == "Attendance Status":
				if not status and employee_day_off_attendance:
					status = employee_day_off_attendance.get(day, "")
				if status in ["Present", "Working", "Work From Home"]:
					working_days += 1

			elif attendance_based_on in ("Shift Hours", "Working Hours"):
				if not status and employee_day_off_attendance:
					status = employee_day_off_attendance.get(day, 0)
				if status and status not in ["Day Off", "Client Day Off", "Absent", "On Leave"]:
					working_days += 1

			if status in ["Day Off", "Client Day Off"]:
				off_days += 1

			row[cstr(day)] = status

		row["working_days"] = working_days
		row["off_days"] = off_days
		
		attendance_values.append(row)

	return attendance_values

def get_ot_attendance_map(filters, attendance_based_on=None):
	non_day_off_attendance_records = get_ot_attendance_records(filters)

	attendance_map = {}

	for d in non_day_off_attendance_records:
		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		if attendance_based_on == "Shift Hours":
			attendance_map[d.employee][d.shift][d.day_of_month] = d.shift_duration
		elif attendance_based_on == "Attendance Status":
			attendance_map[d.employee][d.shift][d.day_of_month] = d.status
		else:
			attendance_map[d.employee][d.shift][d.day_of_month] = d.working_hours

	return attendance_map

def get_ot_attendance_records(filters):
	from frappe.utils import get_last_day
	start_date = f"{filters.year}-{int(filters.month):02d}-01"
	end_date = get_last_day(start_date)

	Attendance = frappe.qb.DocType("Attendance")
	OperationsShift = frappe.qb.DocType("Operations Shift")
	ShiftType = frappe.qb.DocType("Shift Type")

	query = (
		frappe.qb.from_(Attendance)
		.join(OperationsShift)
		.on(Attendance.operations_shift == OperationsShift.name)
		.left_join(ShiftType)
		.on(OperationsShift.shift_type == ShiftType.name)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			OperationsShift.shift_classification.as_("shift"),
			Attendance.working_hours,
			ShiftType.duration.as_("shift_duration")
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.attendance_date >= start_date)
			& (Attendance.attendance_date <= end_date)
			& ~(Attendance.status.isin(["Day Off", "Client Day Off"]))
			& (Attendance.roster_type == "Over-Time")
		)
		.orderby(Attendance.employee, Attendance.attendance_date)
	)

	if filters.get("project"):
		query = query.where(Attendance.project == filters.project)

	if filters.get("site"):
		query = query.where(Attendance.site == filters.site)

	return query.run(as_dict=True)

def get_ot_rows(employee_details, filters, attendance_map, attendance_based_on=None):
	records = []

	day_off_attendance_map = get_day_off_attendance_map(filters, "Over-Time")

	# Pass the actual mode through so OT respects Attendance Status when selected
	ot_mode = attendance_based_on or "Working Hours"

	for employee, details in employee_details.items():
		employee_attendance = attendance_map.get(employee)
		employee_day_off_attendance = day_off_attendance_map.get(employee, {})
		if not employee_attendance:
			# no attendance records found for employee
			continue

		attendance_for_employee = get_attendance_status(filters, employee_attendance, employee_day_off_attendance, ot_mode)

		# set employee details in the first row
		for record in attendance_for_employee:
			record.update({
				"employee": details.name,
				"employee_id": details.employee_id,
				"employee_name": details.employee_name,
				"sale_item": details.sale_item
			})

		records.extend(attendance_for_employee)

	return records


@frappe.whitelist()
def get_sale_item_details(amendment_name: str) -> dict:
	"""Return a map of sale_item → item_type from Contract Item."""
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	doc.check_permission("read")

	sale_items = set()
	for row in doc.get("attendance_details"):
		if row.sale_item:
			sale_items.add(row.sale_item)
	for row in doc.get("overtime_details"):
		if row.sale_item:
			sale_items.add(row.sale_item)

	if not sale_items:
		return {}

	items = frappe.get_list("Item",
		filters={"name": ["in", list(sale_items)]},
		fields=["name", "item_type"]
	)
	return {i.name: i.item_type or "" for i in items}


@frappe.whitelist()
def get_pdf_header_metadata(amendment_name: str) -> dict:
	"""Return metadata needed for the PDF header: logo, company, client, project."""
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	doc.check_permission("read")

	company_name = frappe.defaults.get_user_default("Company") or ""
	logo_url = ""
	client_name = ""

	# Get Letter Head logo
	letter_head_name = ""
	if company_name:
		letter_head_name = frappe.db.get_value("Company", company_name, "default_letter_head") or ""
	if not letter_head_name:
		letter_head_name = frappe.db.get_default("letter_head") or ""
	if letter_head_name:
		# Try the image field first (clean URL)
		logo_url = frappe.db.get_value("Letter Head", letter_head_name, "image") or ""
		if not logo_url:
			# Fallback: extract src from the HTML content field
			import re
			content = frappe.db.get_value("Letter Head", letter_head_name, "content") or ""
			match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
			if match:
				logo_url = match.group(1)

	# Get client from Contract
	if doc.contract:
		client_name = frappe.db.get_value("Contracts", doc.contract, "client") or ""

	return {
		"logo_url": logo_url,
		"company_name": company_name,
		"client_name": client_name,
		"project_name": doc.project or ""
	}