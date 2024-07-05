import frappe, pandas as pd
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate, nowdate, get_link_to_form, format_date
from erpnext.setup.doctype.employee.employee import is_holiday
from hrms.hr.utils import validate_active_employee, validate_dates
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from frappe.model.workflow import apply_workflow
from one_fm.utils import (
	send_workflow_action_email, get_holiday_today, workflow_approve_reject, get_approver, has_super_user_role
)


class AttendanceRequestOverride(AttendanceRequest):
	def validate(self):
		validate_active_employee(self.employee)
		validate_future_dates(self, self.from_date, self.to_date)
		if self.half_day:
			if not getdate(self.from_date) <= getdate(self.half_day_date) <= getdate(self.to_date):
				frappe.throw(_("Half day date should be in between from date and to date"))
		self.set_approver()

	def before_insert(self):
		check_for_attendance(self)

	def set_approver(self):
		if not self.approver and self.employee:
			self.approver = get_approver(self.employee)
			if self.approver:
				approver = frappe.db.get_value(
					"Employee",
					{'name':self.approver},
					['user_id', 'employee_name'],
					as_dict=1
				)
				pass

	def on_submit(self):
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

	def on_update_after_submit(self):
		self.send_notification()
		if self.update_request:
			if self.workflow_state == 'Approved':
				self.create_attendance()
			if self.workflow_state == 'Update Request':
				self.cancel_requested_attendance()

	def get_shift_assignment(self, attendance_date):
		"""
			Check if shift exist for employee
		"""
		if(frappe.db.exists("Shift Assignment",
			{'employee':self.employee, 'docstatus':1, 'status':'Active', 'start_date':attendance_date})):
			shift_assignment = frappe.db.get_list("Shift Assignment",
				{'employee':self.employee, 'docstatus':1, 'status':'Active', 'start_date':attendance_date})
			return frappe.get_doc("Shift Assignment", shift_assignment[0].name)
		return False

	def create_attendance(self):
		date_range = pd.date_range(self.from_date, self.to_date)
		for d in date_range:
			if d.date()<= getdate():
				self.mark_attendance(str(d.date()))

	def get_employee(self):
		return frappe.get_doc("Employee", self.employee)

	def mark_attendance(self, attendance_date):
		try:
			employee = self.get_employee()
			shift_assignment = self.get_shift_assignment(attendance_date)
			working_hours = frappe.db.get_value('Shift Type', shift_assignment.shift_type, 'duration')  if shift_assignment  else 8
			# check if attendance exists
			attendance_name = super(AttendanceRequestOverride, self).get_attendance_record(attendance_date)
			status = "Work From Home" if self.reason == "Work From Home" else "Present"
			if attendance_name:
				# update existing attendance, change the status
				doc = frappe.get_doc("Attendance", attendance_name)
				old_status = doc.status

				if old_status != 'Present':
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
				elif old_status == 'Present' and status == "Work From Home":
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
			frappe.log_error(str(frappe.get_traceback()), 'Attendance Request')


	def send_notification(self):
		if self.workflow_state in ['Pending Approval']:
			send_workflow_action_email(self, [self.approver])
		if self.workflow_state in ['Rejected', 'Approved', 'Update Request', 'Cancelled']:
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
		if frappe.session.user == self.approver or has_super_user_role(employee_user) or (
			frappe.session.user == "administrator"
		):
			return True

		frappe.msgprint('This Attendance Request can only be approved by the employee supervisor')
		return False

def check_for_attendance(doc):
	att = frappe.get_list("Attendance", {"employee": doc.employee, "attendance_date":["between", [doc.from_date, doc.to_date]]}, ['status'])
	if att:
		frappe.msgprint("Your attendance is marked for today as "+ att[0].status )

def validate_future_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", doc.employee, ["date_of_joining", "relieving_date"]
	)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))



@frappe.whitelist()
def update_request(attendance_request, from_date, to_date):
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	attendance_request_obj = frappe.get_doc('Attendance Request', attendance_request)
	validate_future_dates(attendance_request_obj, from_date, to_date)
	attendance_request_obj.db_set("from_date", from_date)
	attendance_request_obj.db_set("to_date", to_date)
	attendance_request_obj.db_set("update_request", True)
	apply_workflow(attendance_request_obj, "Update Request")



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
            frappe.log_error(str(e), 'Attendance Request')
