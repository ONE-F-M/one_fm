from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
import frappe, pandas as pd
from frappe import _
from frappe.utils import getdate, get_link_to_form, format_date, add_days
from erpnext.setup.doctype.employee.employee import is_holiday
from hrms.hr.utils import validate_active_employee
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest

from frappe.desk.form.assign_to import add, remove
from one_fm.utils import (
	send_workflow_action_email, workflow_approve_reject, get_approver, has_super_user_role
)


class AttendanceRequestOverride(AttendanceRequest):
	def validate(self):
		validate_active_employee(self.employee)
		if self.has_value_changed("from_date") or self.has_value_changed("to_date"):
			validate_dates(self, self.from_date, self.to_date)
		if self.half_day:
			if not getdate(self.from_date) <= getdate(self.half_day_date) <= getdate(self.to_date):
				frappe.throw(_("Half day date should be in between from date and to date"))
		self.validate_wfh_before_leave()
		self.set_approver()

	def validate_wfh_before_leave(self):
		if self.reason == "Work From Home":
			# Calculate next working day after to_date
			next_date = add_days(self.to_date, 1)
			
			# Loop to find next working day (skip holidays)
			while is_holiday(self.employee, next_date):
				next_date = add_days(next_date, 1)
			
			# Check if there is an approved Annual Leave starting on next_date
			if frappe.db.sql("""
				select name from `tabLeave Application`
				where employee = %s
				and from_date = %s
				and status = 'Approved'
				and leave_type = 'Annual Leave'
				and docstatus = 1
			""", (self.employee, next_date)):
				frappe.throw(
					_("You cannot select 'Work From Home' for {0} because your annual leave starts on {1}.").format(
						format_date(self.to_date), format_date(next_date)
					)
				)

	def before_insert(self):
		check_for_attendance(self)

	def set_approver(self):
		if self.employee:
			self.approver = get_approver(self.employee)
			if self.approver:
				approver = frappe.db.get_value(
					"Employee",
					{'name':self.approver},
					['user_id', 'employee_name'],
					as_dict=1
				)
				self.approver_name = approver.employee_name
				self.approver_user = approver.user_id

	def on_submit(self):
		if not frappe.flags.get("ignore_supervisor_check", False):
			if not self.reports_to():
				frappe.throw("You are not the employee supervisor")
		self.create_attendance()

	def on_cancel(self):
		self.cancel_requested_attendance()

	def cancel_requested_attendance(self):
		attendance_list = frappe.get_list(
			"Attendance", {"employee": self.employee, "attendance_request": self.name}
		)
		if attendance_list:
			for attendance in attendance_list:
				attendance_obj = frappe.get_doc("Attendance", attendance["name"])
				attendance_obj.cancel()

	def on_update(self):
		self.send_notification()
		self.assign_to_owner()

	def on_update_after_submit(self):
		self.send_notification()
		if self.update_request:
			if self.workflow_state == 'Approved':
				self.create_attendance()

	def get_shift_assignment(self, attendance_date):
		"""
			Check if shift exist for employee
		"""
		shift_check = frappe.db.exists("Shift Assignment",{'employee':self.employee, 'docstatus':1, 'status':'Active', 'start_date':attendance_date})
		return frappe.get_doc("Shift Assignment", shift_check) if shift_check else False

	def create_attendance(self):
		date_range = pd.date_range(self.from_date, self.to_date)
		for d in date_range:
			if d.date() <= getdate():
				self.mark_attendance(str(d.date()))

	def get_employee(self):
		return frappe.get_doc("Employee", self.employee)

	def mark_attendance(self, attendance_date):
		try:
			employee = self.get_employee()
			shift_assignment = self.get_shift_assignment(attendance_date)
			working_hours = frappe.db.get_value('Shift Type', shift_assignment.shift_type, 'duration')  if shift_assignment  else 8
			# check if attendance exists
			attendance_name = self.get_attendance_doc(attendance_date)
			status = "Present" if self.reason == "On Duty" else "Work From Home"
			if attendance_name:
				# update existing attendance, change the status
				doc = frappe.get_doc("Attendance", attendance_name.name)
				old_status = doc.status

				if old_status != status:
					doc.db_set({
						"status": status,
						"attendance_request": self.name,
						"working_hours": working_hours,
						"reference_doctype":"Attendance Request",
						"reference_docname":self.name})
					text = _("Changed the status from {0} to {1} via Attendance Request").format(
						frappe.bold(old_status), frappe.bold(status)
					)
					doc.add_comment(comment_type="Info", text=text)

					frappe.msgprint(
						_("Updated status from {0} to {1} for date {2} in the attendance record {3}").format(
							frappe.bold(old_status),
							frappe.bold(status),
							frappe.bold(format_date(attendance_date)),
							get_link_to_form("Attendance", doc.name),
						),
						title=_("Attendance Updated"),
					)
			else:
				attendance = frappe.new_doc("Attendance")
				attendance.employee = self.employee
				attendance.status = status
				attendance.attendance_date = attendance_date
				attendance.working_hours = working_hours
				attendance.attendance_request = self.name
				attendance.operations_shift = shift_assignment.shift if shift_assignment else ''
				attendance.roster_type = shift_assignment.roster_type if shift_assignment else ''
				attendance.shift = shift_assignment.shift_type if shift_assignment else ''
				attendance.project = shift_assignment.project if shift_assignment else ''
				attendance.site = shift_assignment.site if shift_assignment else ''
				attendance.operations_role = shift_assignment.operations_role if shift_assignment else ''
				attendance.reference_doctype = "Attendance Request"
				attendance.reference_docname = self.name
				attendance.save(ignore_permissions=True)
				attendance.submit()
		except Exception as e:
			frappe.log_error(message=str(frappe.get_traceback()), title='Attendance Request')


	def send_notification(self):
		if self.workflow_state in ['Pending Approval']:
			send_workflow_action_email(self, [self.approver_user])
		if self.workflow_state in ['Rejected', 'Approved', 'Cancelled']:
			workflow_approve_reject(self, recipients=None)

	def validate_if_attendance_not_applicable(self, attendance_date):
		# Check if attendance_date is a Holiday
		if is_holiday(self.employee, attendance_date):
			frappe.msgprint(
				_("Attendance not submitted for {0} as it is a Holiday.").format(attendance_date), alert=1
			)
			return True

		# Check if employee on Leave
		leave_record = frappe.db.sql(
			"""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""",
			(self.employee, attendance_date),
			as_dict=True,
		)
		if leave_record:
			frappe.msgprint(
				_("Attendance not submitted for {0} as {1} on leave.").format(attendance_date, self.employee),
				alert=1,
			)
			return True

		return False

	@frappe.whitelist()
	def reports_to(self):
		employee_user = frappe.get_value("Employee", {"name": self.employee}, "user_id")
		if frappe.session.user == self.approver_user or has_super_user_role(employee_user) or (
			frappe.session.user == "administrator"
		):
			return True

		return False

	def assign_to_owner(self):
		# Assign back to owner if Attendance Request is Returned to Draft state from Pending Approval
		if not self.get("__unsaved"):
			if self.workflow_state == "Draft" and self.get_doc_before_save().workflow_state == "Pending Approval":
				# Remove approver's assignment
				remove(self.doctype, self.name, frappe.session.user, ignore_permissions=False)

				# Assign back to document owner
				add({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': [self.owner],
					'description': (_(f"Attendance Request: {self.name} has been returned to Draft. Please check and review."))
				})
			if self.workflow_state == "Pending Approval" and self.get_doc_before_save().workflow_state == "Draft":
				# Remove doc owner's assignment
				remove(self.doctype, self.name, self.owner, ignore_permissions=False)

def check_for_attendance(doc):
	att = frappe.get_list("Attendance", {"employee": doc.employee, "attendance_date":["between", [doc.from_date, doc.to_date]]}, ['status'])
	if att:
		frappe.msgprint("Your attendance is marked for today as "+ att[0].status )

def validate_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", doc.employee, ["date_of_joining", "relieving_date"]
	)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"), title="Invalid From Date")
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"), title="Invalid From Date")
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"), title="Invalid From Date")
	if getdate(from_date) < getdate():
		if doc.is_new():
			msg = _("Please note that Attendance Request cannot be created for a past date")
		else:
			msg = _("Please note that Attendance Request cannot be updated for a past date")
		frappe.throw(msg, title="Invalid From Date")


def mark_future_attendance_request():
	"""
		GET attendance request for the future where date is today
	"""
	attendance_requests = frappe.db.sql(f"""
		SELECT name FROM `tabAttendance Request`
		WHERE '{getdate()}' BETWEEN from_date AND to_date
		AND docstatus=1
	""", as_dict=1)
	for row in attendance_requests:
		try:
			frappe.get_doc("Attendance Request", row.name).mark_attendance(str(getdate()))
		except Exception as e:
			frappe.log_error(message=str(e), title='Attendance Request')


@frappe.whitelist()
def approve_pending_attendance_request(start_date):
    """
    Get attendance requests for the future where date is today
    and workflow state is 'Pending Approval' and approve it.
    """
    attendance_requests = frappe.db.sql(f"""
        SELECT name FROM `tabAttendance Request`
        WHERE '{start_date}' BETWEEN from_date AND to_date
        AND workflow_state = 'Pending Approval'
    """, as_dict=1)
    for row in attendance_requests:
        try:
            frappe.flags.ignore_supervisor_check = True
            doc = frappe.get_doc("Attendance Request", row.name)
            apply_workflow(doc, "Approve")
        except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title="Attendance Request Marking")


def get_permission_query_conditions(user):
	"""
		Restrict the Attendance Request list (and global search / list filters) to the
		records the current user is entitled to manage: their own requests plus those of
		their direct and indirect reports (the reports_to reporting tree).

		Registered via `permission_query_conditions` in hooks.py. The framework appends the
		returned SQL to every list/report/search query for this DocType, so restricted
		records are hidden entirely rather than blocked only on open.

		Returning an empty string means no restriction (full visibility).

		args:
			user: name of the User (falls back to the current session user)
		return: SQL condition string
	"""
	if not user:
		user = frappe.session.user

	# Platform / admin users see everything
	if user in ("Administrator", "administrator"):
		return ""

	user_roles = frappe.get_roles(user)

	if "System Manager" in user_roles:
		return ""

	# Director / configured ONEFM super user role
	if has_super_user_role(user):
		return ""

	# Roles listed under ONEFM General Setting -> Document Access Roles see everything
	document_access_roles = frappe.get_all(
		"ONEFM Document Access Roles Detail",
		filters={"parentfield": "document_access_roles"},
		pluck="role",
	)
	if any(role in document_access_roles for role in user_roles):
		return ""

	# Everyone else is limited to their own reporting line. Users without a linked
	# Employee have nothing to manage, so they see nothing (privacy first).
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return "1=0"

	# The manager's own record plus all direct and indirect reports down the chain.
	# NOTE: We walk the `reports_to` field instead of using the nested-set (lft/rgt)
	# helpers because the Employee tree's lft/rgt is not maintained on this database
	# (nested-set loop validation is customised), so get_descendants returns nothing.
	employee_names = get_reporting_subtree(employee)

	# Safely escape each value for the IN clause
	escaped = ", ".join(frappe.db.escape(emp) for emp in employee_names)
	return f"`tabAttendance Request`.`employee` in ({escaped})"


def get_reporting_subtree(employee):
	"""
		Return a list containing the given employee plus every direct and indirect
		report, resolved by walking the `reports_to` field level by level.

		This does not rely on the nested-set (lft/rgt) columns, which are not kept in
		sync on this database. Cycles (e.g. an employee reporting to themselves) are
		handled by only expanding employees we have not already seen.
	"""
	subtree = {employee}
	frontier = [employee]

	while frontier:
		direct_reports = frappe.get_all(
			"Employee",
			filters={"reports_to": ["in", frontier]},
			pluck="name",
		)
		frontier = [emp for emp in direct_reports if emp not in subtree]
		subtree.update(frontier)

	return list(subtree)