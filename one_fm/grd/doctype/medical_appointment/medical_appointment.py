# Copyright (c) 2025, one_fm and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate, nowdate, add_days, format_datetime
from one_fm.utils import get_employee_site_supervisor_user, get_approver_user

class MedicalAppointment(Document):
	def validate(self):
		self.validate_appointment_date()
		self.set_approver()

	def validate_appointment_date(self):
		if self.workflow_state not in ["Completed", "Reschedule Requested"]:
			return

		if not self.date_and_time_confirmation:
			frappe.throw(
				_("Date and Time Confirmation is required."),
				title=_("Date and Time Confirmation Required"),
			)

		if getdate(self.date_and_time_confirmation) > getdate(today()):
			frappe.throw(
				_("You are not allowed to action medical appointment before the appointment date."),
				title=_("Appointment Date is in the future"),
			)

	def set_approver(self):
		if not self.employee_supervisor and self.employee:
			employee_supervisor = get_employee_site_supervisor_user(self.employee)
			if not employee_supervisor:
				employee_supervisor = get_approver_user(self.employee)
			self.employee_supervisor = employee_supervisor

	def on_update(self):
		if not self.workflow_state:
			return
		if not self.has_value_changed("workflow_state"):
			return

		self.notify_users_on_workflow_state_change()
		self.set_employee_schedule_and_attendance()

	def notify_users_on_workflow_state_change(self):
		self.notify_employee_supervisor_on_operations_site_rejection()
		self.notify_gr_operator_on_rejection()

	def notify_employee_supervisor_on_operations_site_rejection(self):
		if not self.employee_supervisor:
			return
		if self.workflow_state != "Set Pick-up as Accommodation (Supervisor)":
			return

		message = _(
			"This is to inform you that your request for site pickup for a medical appointment has been rejected. You can change the pickup location to Accommodation.<br/><br/>{0} {1}"
		).format(self.full_name, self.date_and_time_confirmation)

		create_medical_appointment_notification_log(
			self.name,
			message,
			message,
			self.employee_supervisor
		)

	def notify_gr_operator_on_rejection(self):
		if not self.government_relations_operator:
			return
		if self.workflow_state != "Rejected":
			return
		if not self.reason_for_rejection:
			return
		message = _("This is to inform you that a medical appointment has been rejected<br/>")
		message += _("Employee Name: {0}<br/>").format(self.full_name)
		message += _("Date and Time Confirmation: {0}<br/>").format(self.date_and_time_confirmation)
		message += _("Reason for Rejection: {0}").format(self.reason_for_rejection)
		create_medical_appointment_notification_log(
			self.name,
			message,
			message,
			self.government_relations_operator
		)

	def set_employee_schedule_and_attendance(self):
		if self.block_roster != "Yes":
			return
		if self.workflow_state != "Pending PRO":
			return

		self.update_employee_schedule()
		self.create_attendance()

	def update_employee_schedule(self):
		existing_schedule = frappe.db.exists("Employee Schedule",
			{
				"employee": self.employee,
				"date": getdate(self.date_and_time_confirmation),
				"roster_type": "Basic"
			}
		)
		args = {
			"employee_availability": "Medical Appointment",
			"operations_role": "",
			"shift": "",
			"site": "",
			"shift_type": "",
			"project": "",
			"reference_doctype": self.doctype,
			"reference_docname": self.name
		}
		if existing_schedule:
			frappe.db.set_value("Employee Schedule", existing_schedule, args)
		else:
			args.update({
				"employee": self.employee,
				"date": getdate(self.date_and_time_confirmation)
			})
			frappe.get_doc({
				"doctype": "Employee Schedule",
				**args
			}).insert(ignore_permissions=True)

	def create_attendance(self):
		attendance_doc = frappe.get_doc({
			"doctype": "Attendance",
			"attendance_date": getdate(self.date_and_time_confirmation),
			"employee": self.employee,
			"status": "On Hold",
			"comment": _("Created via Medical Appointment: {0}").format(self.name)
		})
		attendance_doc.insert(ignore_permissions=True)
		attendance_doc.submit()

	def on_submit(self):
		self.validate_appointment_date()
		self.validate_payment_invoice_attachment()
		self.update_attendance_status()

	def validate_payment_invoice_attachment(self):
		if self.workflow_state == "Completed" and not self.payment_invoice:
			frappe.throw(
				_("Payment invoice attachment is required to proceed."),
				title=_("Payment Invoice Required"),
			)

	def update_attendance_status(self):
		if self.workflow_state not in ["Completed", "Reschedule Requested"]:
			return
		if self.block_roster != "Yes":
			return

		existing_attendance = frappe.db.exists(
			"Attendance",
			{
				"attendance_date": getdate(self.date_and_time_confirmation),
				"employee": self.employee,
				"status": ["in", ["On Hold", "Absent"]]
			}
		)

		if not existing_attendance:
			return

		attendance_doc = frappe.get_doc("Attendance", existing_attendance)
		attendance_doc.status = "Medical Appointment" if self.workflow_state == "Completed" else "Absent"
		if attendance_doc.status == "Medical Appointment":
			attendance_doc.working_hours = 8
		attendance_doc.comment = _("Updated via Medical Appointment: {0}").format(self.name)
		attendance_doc.save(ignore_permissions=True)
		attendance_doc.submit()


# WI-002095: the medical an overseas hire needs is opened by the Preparation that hires
# them. "First Time" for a first arrival; the field's other option, Renewal, belongs to the
# renewal path, which does not open one.
FIRST_TIME = "First Time"


def create_medical_appointment(employee, appointment_type, preparation_name=None):
	"""Open the medical appointment a Preparation row calls for (WI-002095).

	Inserted without its mandatory fields. The appointment date, whether transport is
	needed and which PRO takes it are not facts anybody holds when the Preparation is
	submitted - the supervisor and the GR Operator supply them as the record moves through
	the workflow, which is what the Pending Supervisor state it opens in is for. Mandatory
	is enforced again on every later save, so nothing reaches submit half-filled.
	"""
	appointment = frappe.new_doc("Medical Appointment")
	appointment.employee = employee.name
	appointment.medical_appointment_type = appointment_type
	appointment.preparation = preparation_name
	appointment.date_of_application = today()
	appointment.insert(ignore_mandatory=True)

	return appointment


@frappe.whitelist()
def send_supervisor_notification_on_pending_medical_appointments():
	pending_appointments = frappe.get_all(
		"Medical Appointment",
		filters={"workflow_state": "Pending Supervisor"},
		fields=["name", "full_name", "employee_supervisor", "employee"],
	)

	for appointment in pending_appointments:
		employee_name = appointment.get("full_name") or appointment.get("employee")
		supervisor = appointment.get("employee_supervisor")

		if not supervisor:
			continue

		message = _("You need to take action on Medical Appointment for {0}").format(employee_name)

		notification_doc = {
			"doctype": "Notification Log",
			"document_type": "Medical Appointment",
			"document_name": appointment.name,
			"for_user": supervisor,
			"subject": message,
			"type": "Alert"
		}
		frappe.get_doc(notification_doc).insert(ignore_permissions=True)

def create_medical_appointment_notification_log(medical_appointment, subject, message, for_user):
	notification_doc = {
		"doctype": "Notification Log",
		"subject": subject,
		"for_user": for_user,
		"document_type": "Medical Appointment",
		"document_name": medical_appointment,
		"email_content": message,
		"type": "Alert"
	}
	frappe.get_doc(notification_doc).insert(ignore_permissions=True)

def send_medical_appointment_reminders():
	"""
	Sends daily reminders to Transportation Supervisors for medical appointments
	scheduled for the next day.
	"""
	tomorrow_date = getdate(add_days(nowdate(), 1))

	appointments_by_supervisor = get_appointments_for_supervisor(tomorrow_date)

	for supervisor, supervisor_appointments in appointments_by_supervisor.items():
		pickup_locations_list = []
		for appointment in supervisor_appointments:
			pickup_time = format_datetime(appointment.date_and_time_confirmation, "hh:mm a")
			pickup_location_name = ""
			if appointment.pickup_location == "Operations Site" and appointment.operations_site:
				pickup_location_name = appointment.operations_site
			elif appointment.pickup_location == "Accommodation" and appointment.accommodation_name:
				pickup_location_name = appointment.accommodation_name

			if pickup_location_name:
				pickup_locations_list.append(
					f"<li>{appointment.full_name}: {pickup_time} from {pickup_location_name}</li>"
				)

		if not pickup_locations_list:
			continue

		pickup_locations_html = f"<ol>{''.join(pickup_locations_list)}</ol>"

		email_content = f"""
		<p>You have {len(supervisor_appointments)} employees scheduled to attend medical appointments on {format_datetime(tomorrow_date, 'd MMMM YYYY')}.</p>
		<p>Pick-up locations:</p>
		{pickup_locations_html}
		"""

		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": supervisor,
				"document_type": "Medical Appointment",
				"subject": f"Reminder: {len(supervisor_appointments)} medical appointments for tomorrow.",
				"email_content": email_content,
			},
		).insert(ignore_permissions=True)

def get_appointments_for_supervisor(tomorrow_date):
	tomorrow_start = f"{tomorrow_date} 00:00:00"
	tomorrow_end = f"{tomorrow_date} 23:59:59"

	appointments = frappe.get_all(
		"Medical Appointment",
		filters={
			"workflow_state": "Pending Transportation Supervisor",
			"date_and_time_confirmation": ["between", (tomorrow_start, tomorrow_end)],
			"transportation_supervisor_user": ('is', 'set')
		},
		fields=[
			"full_name",
			"date_and_time_confirmation",
			"transportation_supervisor_user",
			"pickup_location",
			"operations_site",
			"accommodation_name",
		],
	)

	if not appointments:
		return {}

	# Group appointments by supervisor
	appointments_by_supervisor = {}
	for appointment in appointments:
		supervisor = appointment.get("transportation_supervisor_user")
		if supervisor not in appointments_by_supervisor:
			appointments_by_supervisor[supervisor] = []
		appointments_by_supervisor[supervisor].append(appointment)

	return appointments_by_supervisor