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

		# Enforce remarks when returning to Draft
		if not self.is_new() and self.workflow_state == "Draft":
			old_state = frappe.db.get_value("Subcontract Staff Attendance", self.name, "workflow_state")
			if old_state in ["Pending Operations Supervisor", "Pending Project Manager"]:
				has_remarks = any(row.remarks for row in self.get("subcontractor_staff_attendance_item", []))
				if not has_remarks:
					frappe.throw("You must provide a remark for at least one employee when returning the document to Draft.")

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
				
				day_data = compare_against.get("days", {}).get(str(i), {})
				
				# Ignore baseline data if it belongs to a different site
				if day_data.get("site") and day_data.get("site") != self.site:
					old_val = None
				else:
					old_val = day_data.get("value")

				# Normalize
				if new_val is None: new_val = "" if self.attendance_record_based_on == "Attendance Status" else 0.0
				if old_val is None: old_val = "" if self.attendance_record_based_on == "Attendance Status" else 0.0

				if self.attendance_record_based_on == "Shift Hours":
					try:
						n_val = float(new_val or 0.0)
					except (ValueError, TypeError):
						n_val = 0.0
					try:
						o_val = float(old_val or 0.0)
					except (ValueError, TypeError):
						o_val = 0.0
						
					if n_val != o_val:
						new_logs.append(f"{field_type} for Day {i} has been updated to [{n_val}] from [{o_val}].")
				else:
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
		fields=["employee", "attendance_date", "status", "working_hours", "site", "project"]
	)

	# Map attendances: { employee_id: { day_int: { status: "Present", hours: 8.0, site: "Site A" } } }
	attendance_map = {}
	for att in attendances:
		emp = att.employee
		from frappe.utils import getdate
		day = getdate(att.attendance_date).day
		
		if emp not in attendance_map:
			attendance_map[emp] = {}
			
		attendance_map[emp][day] = {
			"status": att.status,
			"hours": att.working_hours or 0.0,
			"site": att.site,
			"project": att.project
		}

	items = []
	for emp in employees:
		item = {
			"employee": emp.name,
			"employee_id": emp.name,
			"employee_name": emp.employee_name,
			"days": {}
		}
		
		emp_attendance = attendance_map.get(emp.name, {})
		
		for i in range(1, 32):
			day_data = emp_attendance.get(i)
			if day_data and day_data.get("site"):
				if attendance_record_based_on == "Attendance Status":
					item["days"][str(i)] = {
						"value": day_data["status"],
						"site": day_data["site"],
                        "project": day_data["project"],
						"status": None,  # no workflow state yet
						"status_val": day_data["status"]
					}
				else:
					item["days"][str(i)] = {
						"value": day_data["hours"],
						"site": day_data["site"],
                        "project": day_data["project"],
						"status": None,
						"status_val": day_data["status"]
					}
		
		items.append(item)
		
	return items


@frappe.whitelist()
def save_attendance_records(subcontractor_name, from_date, to_date, based_on, rows_json, submit=0):
	import json
	rows = json.loads(rows_json)
	
	# payload rows: list of { employee, employee_name, days: { "1": { value, site, status, parent_doc, project } } }
	# Structure the data by site
	site_data = {} # { site: { project: list_of_flat_rows } }

	for emp in rows:
		# Group the employee's days by valid site so we can reconstruct flat rows
		emp_sites = {}
		
		for d_str, cell in emp.get("days", {}).items():
			site = cell.get("site")
			if not site: continue
			
			if site not in emp_sites:
				emp_sites[site] = {}
			emp_sites[site][d_str] = cell
			
		# Build the flat row dictionary matching the child table for each site
		for site, site_days in emp_sites.items():
			project = None
			for c in site_days.values():
				if c.get("project"):
					project = c.get("project")
					break
					
			if site not in site_data:
				site_data[site] = {"project": project, "employees": []}
				
			flat_row = {
				"employee": emp.get("employee"),
				"employee_name": emp.get("employee_name")
			}
			
			for i in range(1, 32):
				cell = site_days.get(str(i))
				if cell:
					if based_on == "Attendance Status":
						flat_row[f"day_{i}"] = cell.get("value")
					else:
						flat_row[f"day_{i}_hour"] = cell.get("value")
						
			site_data[site]["employees"].append(flat_row)
            
	# Now create or update backend records
	affected_docs = []
	for site, site_info in site_data.items():
		project = site_info["project"]
		
		# Does doc exist?
		existing = frappe.get_all(
			"Subcontract Staff Attendance",
			filters={
				"subcontractor_name": subcontractor_name,
				"from_date": from_date,
				"to_date": to_date,
				"site": site
			},
			fields=["name", "workflow_state"]
		)
		
		if existing:
			doc = frappe.get_doc("Subcontract Staff Attendance", existing[0].name)
			if doc.workflow_state in ["Draft"]:
				doc.attendance_record_based_on = based_on
				doc.set("subcontractor_staff_attendance_item", [])
				for emp_row in site_info["employees"]:
					doc.append("subcontractor_staff_attendance_item", emp_row)
				
				# Call process_audit_logs manually or rely on before_save
				doc.save(ignore_permissions=True)
				affected_docs.append(doc)
		else:
			doc = frappe.new_doc("Subcontract Staff Attendance")
			doc.subcontractor_name = subcontractor_name
			doc.from_date = from_date
			doc.to_date = to_date
			doc.attendance_record_based_on = based_on
			doc.site = site
			if project:
				doc.project = project
				
			for emp_row in site_info["employees"]:
				doc.append("subcontractor_staff_attendance_item", emp_row)
				
			doc.insert(ignore_permissions=True)
			affected_docs.append(doc)
			
	# Commit the saved drafts first so we don't lose the user's edits
	frappe.db.commit()

	# If submit == 1, transition all Draft docs in this period stringently
	if int(submit) == 1:
		from frappe.model.workflow import apply_workflow
		all_docs = frappe.get_all(
			"Subcontract Staff Attendance",
			filters={
				"subcontractor_name": subcontractor_name,
				"from_date": from_date,
				"to_date": to_date,
				"workflow_state": "Draft"
			},
			fields=["name", "site"]
		)
		
		for d in all_docs:
			doc_obj = frappe.get_doc("Subcontract Staff Attendance", d.name)
			try:
				# Mute messages to prevent "No permission to share" warnings from popping up
				frappe.flags.mute_messages = True
				apply_workflow(doc_obj, "Submit for Review")
			except Exception as e:
				frappe.log_error(message=str(e), title=f"Error Submitting Subcontract Attendance {d.name}")
			finally:
				frappe.flags.mute_messages = False

	return "Success"
