import frappe

from one_fm.grd.processa import retire_workflow

# The two daily reminders now run as Processa timer processes.
REMINDER_METHODS = (
	"one_fm.grd.doctype.medical_appointment.medical_appointment.send_supervisor_notification_on_pending_medical_appointments",
	"one_fm.grd.doctype.medical_appointment.medical_appointment.send_medical_appointment_reminders",
)


def execute():
	retire_workflow(
		"Medical Appointment",
		"Medical Appointment",
		(
			"Action Medical Appointment - PRO",
			"Action Medical Appointment - Supervisor",
			"Action Medical Appointment - Transportation Supervisor",
			"Confirm Site Pickup for Medical Appointment - GR Operator",
		),
	)

	for method in REMINDER_METHODS:
		frappe.db.set_value("Process Task", {"method": method}, "is_active", 0)
		frappe.db.delete("Scheduled Job Type", {"method": method})
