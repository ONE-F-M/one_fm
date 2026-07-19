# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_url_to_form


class RamboAssignment(Document):
	def after_insert(self):
		self.send_shift_supervisor_notification()

	def on_submit(self):
		self.create_employee_schedule()
		self.send_submission_notifications()

	def on_cancel(self):
		self.delete_employee_schedule()

	def create_employee_schedule(self):
		"""Create or update an Employee Schedule record for this Rambo Assignment."""
		if not self.employee:
			frappe.throw(_("Reliever Employee is required to create an Employee Schedule."))
		if not self.date:
			frappe.throw(_("Date is required to create an Employee Schedule."))
		if not self.operations_shift:
			frappe.throw(_("Operations Shift is required to create an Employee Schedule."))

		# Get shift type from Operations Shift, then get start/end times from Shift Type
		shift_type = frappe.db.get_value("Operations Shift", self.operations_shift, "shift_type")
		if not shift_type:
			frappe.throw(_("Shift Type is not configured for Operations Shift {0}.").format(self.operations_shift))

		start_time, end_time = frappe.db.get_value(
			"Shift Type", shift_type, ["start_time", "end_time"]
		)

		# Calculate end_date — if shift crosses midnight, end date is next day
		end_date = self.date
		if start_time > end_time:
			end_date = add_days(self.date, 1)

		start_datetime = "{0} {1}".format(self.date, start_time)
		end_datetime = "{0} {1}".format(end_date, end_time)

		# Check if an Employee Schedule already exists for the same employee + date + roster_type
		existing_schedule = frappe.db.get_value(
			"Employee Schedule",
			{"employee": self.employee, "date": self.date, "roster_type": self.roster_type},
			"name"
		)

		if existing_schedule:
			# Cancel any existing Shift Assignment linked to this schedule
			# BEFORE updating it, so the background job can create a new SA
			# with the correct Rambo shift details.
			self._cancel_stale_shift_assignment(existing_schedule, shift_type)

			# Update the existing record
			frappe.db.set_value("Employee Schedule", existing_schedule, {
				"employee_availability": "Working",
				"shift": self.operations_shift,
				"shift_type": shift_type,
				"operations_role": self.operations_role,
				"site": self.operations_site,
				"project": self.project,
				"start_datetime": start_datetime,
				"end_datetime": end_datetime,
				"is_rambo_schedule": 1,
				"rambo_assignment": self.name,
			})
			frappe.msgprint(
				_("Employee Schedule {0} has been updated for {1}.").format(existing_schedule, self.employee_name),
				indicator="blue",
				alert=True
			)
		else:
			# Create a new Employee Schedule record
			schedule = frappe.get_doc({
				"doctype": "Employee Schedule",
				"employee": self.employee,
				"date": self.date,
				"employee_availability": "Working",
				"shift": self.operations_shift,
				"shift_type": shift_type,
				"operations_role": self.operations_role,
				"site": self.operations_site,
				"project": self.project,
				"roster_type": self.roster_type,
				"start_datetime": start_datetime,
				"end_datetime": end_datetime,
				"is_rambo_schedule": 1,
				"rambo_assignment": self.name,
			})
			schedule.flags.ignore_permissions = True
			schedule.insert()
			frappe.msgprint(
				_("Employee Schedule {0} has been created for {1}.").format(schedule.name, self.employee_name),
				indicator="green",
				alert=True
			)

	def delete_employee_schedule(self):
		"""Delete the Employee Schedule record linked to this Rambo Assignment."""
		schedule_name = frappe.db.get_value(
			"Employee Schedule",
			{"rambo_assignment": self.name},
			"name"
		)
		if schedule_name:
			frappe.delete_doc("Employee Schedule", schedule_name, ignore_permissions=True)
			frappe.msgprint(
				_("Employee Schedule {0} has been deleted.").format(schedule_name),
				indicator="orange",
				alert=True
			)

	def _cancel_stale_shift_assignment(self, schedule_name, new_shift_type):
		"""Cancel the Shift Assignment linked to a schedule if it is stale.

		A Shift Assignment is considered stale when:
		  - It is submitted (docstatus=1)
		  - Its shift_type differs from the new Rambo shift_type
		    (meaning it was created for the OLD shift before Rambo)
		  - It has NO Employee Checkin logs (the employee never started it)

		Args:
			schedule_name: str, name of the Employee Schedule being updated.
			new_shift_type: str, the Rambo shift_type that will replace the old one.
		"""
		existing_sa = frappe.db.get_value(
			"Shift Assignment",
			{"employee_schedule": schedule_name, "docstatus": 1},
			["name", "shift_type"],
			as_dict=True
		)

		if not existing_sa:
			return

		# Only cancel if the shift_type is different (stale)
		if existing_sa.shift_type == new_shift_type:
			return

		# Safety check: do NOT cancel if employee has checkin logs
		has_checkin_logs = frappe.db.exists(
			"Employee Checkin",
			{"shift_assignment": existing_sa.name}
		)

		if has_checkin_logs:
			frappe.msgprint(
				_("Shift Assignment {0} has checkin logs and cannot be cancelled.").format(existing_sa.name),
				indicator="orange",
				alert=True
			)
			return

		try:
			sa_doc = frappe.get_doc("Shift Assignment", existing_sa.name)
			sa_doc.flags.ignore_permissions = True
			sa_doc.cancel()
			frappe.msgprint(_("Cancelled stale Shift Assignment {0} (old shift: {1}).").format(
					existing_sa.name, existing_sa.shift_type
				),
				indicator="blue",
				alert=True
			)
			frappe.logger("rambo").info(
				"Cancelled stale Shift Assignment {0} for schedule {1} "
				"(old shift_type: {2}, new: {3})".format(
					existing_sa.name, schedule_name,
					existing_sa.shift_type, new_shift_type
				)
			)
		except Exception:
			frappe.log_error(
				title=_("Rambo Assignment — Cancel Stale SA"),
				message=frappe.get_traceback()
			)


	def _build_email_context(self):
		"""Build the render context for the Rambo Assignment email template."""
		return {
			"date": self.date,
			"original_employee": self.original_employee or "",
			"original_employee_name": self.original_employee_name or "",
			"employee": self.employee or "",
			"employee_name": self.employee_name or "",
			"operations_site": self.operations_site or "",
			"operations_shift": self.operations_shift or "",
			"operations_role": self.operations_role or "",
			"project": self.project or "",
			"start_time": self.start_time or "",
			"end_time": self.end_time or "",
			"transportation_manifest": self.transportation_manifest or "",
			"manifest_url": get_url_to_form(
				"Transportation Manifest", self.transportation_manifest
			),
		}

	def _send_rambo_email(self, recipients):
		"""Render the table-format template and email it to the given recipients."""
		# Deduplicate and drop empty recipients so we never send to a blank address.
		recipients = list({r for r in recipients if r})
		if not recipients:
			return

		message = frappe.render_template(
			"one_fm/templates/emails/rambo_assignment_notification.html",
			self._build_email_context()
		)

		subject = _("Rambo Reliever Assigned for Manifest {0}").format(
			self.transportation_manifest
		)

		try:
			from one_fm.processor import sendemail
			sendemail(
				recipients=recipients,
				subject=subject,
				header=[_("Rambo Assignment Alert: {0}").format(self.name)],
				message=message,
			)
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=_("Rambo Assignment Email Error for {0}").format(self.name)
			)

	def send_shift_supervisor_notification(self):
		"""Send email notification to the Shift Supervisor when a Rambo Assignment is created."""
		if not self.shift_supervisor_user:
			return
		self._send_rambo_email([self.shift_supervisor_user])

	def send_submission_notifications(self):
		"""On submission, notify management by email and the reliever by mobile push.

		Email recipients:
		  1. The Operation Admin configured in Operation Settings.
		  2. The Site Supervisor responsible for the reliever's allocated site
		     (Employee.site -> Operations Site.site_supervisor -> user_id).
		"""
		from one_fm.utils import get_employee_site_supervisor_user

		operation_admin = frappe.db.get_single_value("Operation Settings", "operation_admin")

		site_supervisor_user = None
		if self.employee:
			site_supervisor_user = get_employee_site_supervisor_user(self.employee)

		self._send_rambo_email([operation_admin, site_supervisor_user])

		self.send_reliever_mobile_notification()

	def send_reliever_mobile_notification(self):
		"""Push an immediate deployment alert to the reliever's mobile app.

		The push helper resolves the reliever's device token from Employee.fcm_token
		and silently skips (logging errors) when no token is registered, so a reliever
		who has never logged into the app never blocks submission.
		"""
		if not self.employee:
			return

		from one_fm.utils import send_push_notification

		title = _("Rambo Reliever Deployment")
		body = _("Site: You have been deployed at {0} | Shift: {1} ({2}). Report immediately.").format(
			self.operations_site or "",
			self.operations_shift or "",
			self.date or "",
		)

		send_push_notification(self.employee, title, body)
