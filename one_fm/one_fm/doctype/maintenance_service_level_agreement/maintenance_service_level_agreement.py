# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, formatdate, getdate, get_url_to_form, today


class MaintenanceServiceLevelAgreement(Document):
	def validate(self):
		self.validate_single_enabled_sla_per_client()
		self.validate_date_range()
		self.validate_default_priority()
		self.set_default_priority()
		self.validate_priority_fields()

	def validate_single_enabled_sla_per_client(self):
		"""Block a second enabled Service Level Agreement for the same client.

		A "client" is a Customer entity. When this SLA is enabled and targets a
		specific Customer, ensure no other enabled SLA (Draft or Submitted, i.e.
		not cancelled) already exists for that same customer.
		"""
		if not self.enabled or self.entity_type != "Customer" or not self.entity:
			return

		existing = frappe.get_all(
			"Maintenance Service Level Agreement",
			filters={
				"enabled": 1,
				"entity_type": "Customer",
				"entity": self.entity,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
			limit=1,
		)

		if existing:
			frappe.throw(
				_(
					"An active Service Level Agreement already exists"
					" for this client. You must modify the existing agreement before a"
					" new one can be saved."
				)
			)

	def validate_date_range(self):
		"""Ensure start_date is before end_date when both are specified."""
		if self.start_date and self.end_date:
			if getdate(self.start_date) > getdate(self.end_date):
				frappe.throw(_("End Date cannot be before Start Date"))

	def validate_default_priority(self):
		"""Validate that exactly one priority row is marked as default."""
		default_count = sum(1 for d in self.priorities if d.default_priority)

		if default_count == 0:
			frappe.throw(
				_("Please set exactly one priority as the Default Priority in the Priorities table")
			)
		elif default_count > 1:
			frappe.throw(
				_("Only one priority can be marked as Default Priority. Found {0}").format(
					default_count
				)
			)

	def set_default_priority(self):
		"""Auto-populate the parent default_priority field from the marked row."""
		for d in self.priorities:
			if d.default_priority:
				self.default_priority = d.priority
				break

	def validate_priority_fields(self):
		"""Validate that mandatory fields in priority rows are properly filled.

		Halts submission if First Response Time or maintenance hours are blank,
		and highlights the incomplete rows as per Story 5 acceptance criteria.
		"""
		for idx, row in enumerate(self.priorities, start=1):
			if not row.response_time:
				frappe.throw(
					_("Row {0}: First Response Time is mandatory in the Priorities table").format(idx)
				)
			if not row.maintenance_hours_from:
				frappe.throw(
					_("Row {0}: Maintenance Hours From is mandatory in the Priorities table").format(idx)
				)
			if not row.maintenance_hours_to:
				frappe.throw(
					_("Row {0}: Maintenance Hours To is mandatory in the Priorities table").format(idx)
				)


def send_sla_expiration_warnings():
	"""Daily scheduler: alert the Maintenance Manager 30 days before an SLA expires.

	Runs as part of the daily operational check. For every enabled, submitted
	Maintenance Service Level Agreement whose End Date is exactly 30 calendar days
	from today, a high-priority email is sent to the Maintenance Manager user
	configured in Maintenance Settings.
	"""
	target_date = add_days(today(), 30)

	# get_all is appropriate here: background scheduler job, no user context.
	agreements = frappe.get_all(
		"Maintenance Service Level Agreement",
		filters={
			"enabled": 1,
			"docstatus": 1,
			"end_date": target_date,
		},
		fields=["name", "entity_type", "entity", "end_date"],
	)

	if not agreements:
		return

	maintenance_manager = frappe.db.get_single_value(
		"Maintenance Settings", "maintenance_manager_user"
	)

	if not maintenance_manager:
		frappe.log_error(
			title=_("SLA Expiration Warning Skipped"),
			message=_(
				"No Maintenance Manager User is set in Maintenance Settings; "
				"{0} SLA expiration warning(s) could not be sent."
			).format(len(agreements)),
		)
		return

	for agreement in agreements:
		try:
			send_single_sla_expiration_warning(agreement, maintenance_manager)
		except Exception:
			frappe.log_error(
				title=_("SLA Expiration Warning Error"),
				message=frappe.get_traceback(),
			)


def send_single_sla_expiration_warning(agreement, recipient):
	"""Render and send the expiration warning email for a single SLA."""
	# "Client Name" is the linked Customer entity; non-Customer SLAs show entity as-is.
	client_name = agreement.entity if agreement.entity_type == "Customer" else (agreement.entity or "")

	context = {
		"doc": agreement,
		"client_name": client_name,
		"end_date": formatdate(agreement.end_date),
		"sla_url": get_url_to_form("Maintenance Service Level Agreement", agreement.name),
	}

	message = frappe.render_template(
		"one_fm/templates/emails/sla_expiration_warning.html",
		context,
	)

	subject = _("SLA Expiration Warning: {0} for {1} expires in 30 Days").format(
		agreement.name, client_name
	)

	from one_fm.processor import sendemail

	sendemail(
		recipients=[recipient],
		subject=subject,
		header=[_("SLA Expiration Warning")],
		message=message,
	)
