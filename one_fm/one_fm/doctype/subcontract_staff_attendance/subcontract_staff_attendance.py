# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class SubcontractStaffAttendance(Document):
	def before_save(self):
		if not self.subcontractor_name and frappe.session.user != "Guest":
			supplier = frappe.db.get_value(
				"User Permission",
				{"user": frappe.session.user, "allow": "Supplier"},
				"for_value"
			)
			if supplier:
				self.subcontractor_name = supplier

		self.process_audit_logs()

	def validate(self):
		from frappe.utils import getdate, today
		from dateutil.relativedelta import relativedelta

		# Story 1: Date-wise Validation (10-day buffer)
		if self.to_date:
			to_date = getdate(self.to_date)
			allowed_date = (to_date + relativedelta(months=1)).replace(day=11)
			if getdate(today()) < allowed_date:
				frappe.throw(f"You cannot select a billing month until the 11th of the following month. For {to_date.strftime('%B %Y')}, you must wait until {allowed_date.strftime('%B %d, %Y')}.")

		if not self.get("subcontractor_staff_attendance_item") and self.subcontractor_name:
			self.fetch_subcontractor_staff()

	def process_audit_logs(self):
		if not self.get("subcontractor_staff_attendance_item"):
			return

		# Generate the baseline data by querying the raw Attendance records for this period
		baseline_data = {}
		if getattr(self, "flags", {}).get("_is_fetching_baseline"):
			return

		try:
			self.flags._is_fetching_baseline = True
			baseline_items = api_fetch_subcontractor_staff(
				self.subcontractor_name, self.from_date, self.to_date, self.attendance_record_based_on
			)
			for item in baseline_items:
				baseline_data[item["employee"]] = item
		except Exception:
			baseline_data = {}
		finally:
			self.flags._is_fetching_baseline = False

		for row in self.get("subcontractor_staff_attendance_item"):
			# Always compare against the baseline fetched attendance record
			compare_against = baseline_data.get(row.employee, {})

			new_logs = []
			working_days = 0
			off_days = 0

			for i in range(1, 32):
				field_type = "Attendance Status" if self.attendance_record_based_on == "Attendance Status" else "Shift Hours"
				compare_field = f"day_{i}" if self.attendance_record_based_on == "Attendance Status" else f"day_{i}_hour"

				new_val = row.get(compare_field)
				old_val = compare_against.get(compare_field)

				# Normalize
				if new_val is None: new_val = "" if self.attendance_record_based_on == "Attendance Status" else 0.0
				if old_val is None: old_val = "" if self.attendance_record_based_on == "Attendance Status" else 0.0

				if str(new_val) != str(old_val):
					new_logs.append(f"{field_type} for Day {i} has been updated to [{new_val}] from [{old_val}].")
					
				# Recalculate totals dynamically
				if self.attendance_record_based_on == "Attendance Status":
					if new_val in ["Present", "Half Day", "Work From Home", "Holiday"]:
						working_days += 1
					elif new_val in ["Day Off", "Client Day Off"]:
						off_days += 1
				elif self.attendance_record_based_on == "Shift Hours":
					try:
						if float(new_val) > 0:
							working_days += 1
					except (ValueError, TypeError):
						pass

			# Commit recalculated values to the row
			row.working_days = working_days
			row.off_days = off_days

			if new_logs:
				row.comment = "\n".join(new_logs)
			else:
				row.comment = None

	@frappe.whitelist()
	def fetch_subcontractor_staff(self):
		if not self.subcontractor_name:
			frappe.throw("Please select a Subcontractor Name first.")
		if not self.from_date or not self.to_date:
			frappe.throw("Please specify From Date and To Date.")

		# Ensure the grid is cleared before fetching new records
		self.set("subcontractor_staff_attendance_item", [])

		# Use the unified API logic that dynamically evaluates actual Attendance records
		items = api_fetch_subcontractor_staff(
			self.subcontractor_name,
			self.from_date,
			self.to_date,
			self.attendance_record_based_on
		)

		if items:
			for row in items:
				self.append("subcontractor_staff_attendance_item", row)

	@frappe.whitelist()
	def generate_invoice(self):
		if self.workflow_state != "Approved":
			frappe.throw("Attendance Record must be Approved to generate an invoice.")

		from frappe.utils import getdate

		# Find the Subcontractor Contract
		contract = frappe.get_all(
			"Subcontractor Contracts",
			filters={"subcontractor_name": self.subcontractor_name, "workflow_state": "Active"},
			fields=["name"]
		)
		if not contract:
			frappe.throw(f"No Active Subcontractor Contract found for Supplier: {self.subcontractor_name}")

		contract_doc = frappe.get_doc("Subcontractor Contracts", contract[0].name)

		# Map Item Code -> Contract Item dict
		contract_items = {}
		for row in contract_doc.subcontractor_items:
			contract_items[row.item_code] = row

		# Group employees by Item Code
		item_grouping = {} # { item_code: {"attended_qty": 0.0, "employees": set()} }

		for row in self.subcontractor_staff_attendance_item:
			emp_doc = frappe.get_cached_doc("Employee", row.employee)
			if not getattr(emp_doc, "custom_operations_role_allocation", None):
				frappe.throw(f"Employee {emp_doc.name} missing Operations Role Allocation.")

			ops_role = frappe.get_cached_doc("Operations Role", emp_doc.custom_operations_role_allocation)
			if not ops_role.sale_item:
				frappe.throw(f"Operations Role {ops_role.name} missing Sale Item mapping.")

			item_code = ops_role.sale_item

			if item_code not in contract_items:
				frappe.throw(f"Item Code {item_code} mapped for Employee {emp_doc.name} not found in Subcontractor Contract {contract_doc.name}")

			if item_code not in item_grouping:
				item_grouping[item_code] = {"attended_qty": 0.0, "employees": set()}

			item_grouping[item_code]["employees"].add(row.employee)

			if self.attendance_record_based_on == "Attendance Status":
				item_grouping[item_code]["attended_qty"] += float(row.working_days or 0.0)
			else:
				# Even if based on shift hours, the requirement "sum the total attended days/shifts" 
				# generally implies working_days holds this count.
				item_grouping[item_code]["attended_qty"] += float(row.working_days or 0.0)

		# Build Purchase Invoice
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = self.subcontractor_name
		pi.posting_date = frappe.utils.today()

		# For monthly required days
		import calendar
		to_date_obj = getdate(self.to_date)
		days_in_month = calendar.monthrange(to_date_obj.year, to_date_obj.month)[1]

		for item_code, data in item_grouping.items():
			c_item = contract_items[item_code]
			
			if c_item.rate_type == "Daily":
				accepted_qty = data["attended_qty"]
			elif c_item.rate_type == "Monthly":
				required_days = days_in_month * c_item.count
				accepted_qty = (data["attended_qty"] / required_days) * c_item.count if required_days > 0 else 0
			else:
				accepted_qty = data["attended_qty"]

			# Story 5 Validation
			if c_item.rate_type == "Monthly" and (accepted_qty > c_item.count or (accepted_qty - c_item.count > 0.001)):
				frappe.throw(
					f"Cannot bill more than the contract count for item {item_code}. "
					f"(Calculated Qty: {accepted_qty}, Contract Count: {c_item.count})"
				)

			pi.append("items", {
				"item_code": item_code,
				"qty": accepted_qty,
				"rate": c_item.rate,
				"amount": accepted_qty * c_item.rate
			})

		pi.is_subcontracted = 1
		pi.insert()
		return pi.name


@frappe.whitelist()
def api_fetch_subcontractor_staff(subcontractor_name, from_date, to_date, attendance_record_based_on):
	if not subcontractor_name:
		frappe.throw("Please select a Subcontractor Name first.")
	if not from_date or not to_date:
		frappe.throw("Please specify From Date and To Date.")
	if to_date < from_date:
		frappe.throw("To Date must be greater than or equal to From Date.")

	employees = frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
			"employment_type": "Subcontractor",
			"custom_subcontractor_name": subcontractor_name
		},
		fields=["name", "employee_name"]
	)

	if not employees:
		return []

	# Fetch actual attendance records for these employees in the date range
	employee_ids = [emp.name for emp in employees]
	attendances = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", employee_ids],
			"attendance_date": ["between", [from_date, to_date]],
			"docstatus": ["<", 2]
		},
		fields=["employee", "attendance_date", "status", "working_hours"]
	)

	# Map attendances: { employee_id: { day_int: { status: "Present", hours: 8.0 } } }
	attendance_map = {}
	for att in attendances:
		emp = att.employee
		day = getdate(att.attendance_date).day
		
		if emp not in attendance_map:
			attendance_map[emp] = {}
			
		attendance_map[emp][day] = {
			"status": att.status,
			"hours": att.working_hours or 0.0
		}

	items = []
	
	for emp in employees:
		item = {
			"employee": emp.name,
			"employee_id": emp.name,
			"employee_name": emp.employee_name
		}
		
		emp_attendance = attendance_map.get(emp.name, {})
		
		working_days = 0
		off_days = 0

		for i in range(1, 32):
			day_data = emp_attendance.get(i)
			
			if attendance_record_based_on == "Attendance Status":
				status = day_data["status"] if day_data else ""
				item[f"day_{i}"] = status
				if status in ["Present", "Half Day", "Work From Home", "Holiday"]:
					working_days += 1
				elif status in ["Day Off", "Client Day Off"]:
					off_days += 1
			elif attendance_record_based_on == "Shift Hours":
				hours = day_data["hours"] if day_data else 0.0
				item[f"day_{i}_hour"] = hours
				if hours > 0:
					working_days += 1
		
		item["working_days"] = working_days
		item["off_days"] = off_days
		
		items.append(item)
		
	return items
