# Copyright (c) 2025, one_fm and contributors
# For license information, please see license.txt
"""An employee's medical appointment.

The Medical Appointment Lifecycle process moves it through its states and runs its side
effects. The Medical Appointment Supervisor Reminder and Pickup Reminder processes send the
daily reminders.
"""

from frappe.model.document import Document


class MedicalAppointment(Document):
	pass
