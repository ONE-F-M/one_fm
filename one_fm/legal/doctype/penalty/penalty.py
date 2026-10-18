# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils import add_to_date, cint, flt, get_link_to_form, getdate, nowdate

from one_fm.api.notification import create_notification_log

# The penalty matrix has six occurrence columns; the sixth (Termination) applies from then on.
MAX_OCCURRENCE = 6


class Penalty(Document):
	def before_insert(self):
		if not self.recipient_user and self.recipient_employee:
			self.recipient_user = frappe.db.get_value("Employee", self.recipient_employee, "user_id")
		self.set_occurrences()

	def validate(self):
		self.validate_self_issuance()

	def after_insert(self):
		self.notify_employee()

	def validate_self_issuance(self):
		if self.recipient_employee == self.issuer_employee:
			frappe.throw(_("Penalty recepient and issuer cannot be the same Employee."))

	def notify_employee(self):
		if not self.recipient_user:
			return
		issuer_name = self.issuer_name or "Administrator"
		subject = _("Penalty Issued by {0}.").format(issuer_name)
		message = _("You have been issued a penalty.<br>Link: {0}").format(get_link_to_form(self.doctype, self.name))
		create_notification_log(subject, message, [self.recipient_user], self)

	def set_occurrences(self):
		"""Number each penalty type by the employee's earlier penalties of that type in the
		one-year period, and take the levy and deduction days for that occurrence from the
		active penalty matrix, so the deduction is known at issuance."""
		occurrence_date = getdate(self.penalty_occurence_time or self.penalty_issuance_time or nowdate())

		for row in self.penalty_details:
			if not row.penalty_type:
				continue

			latest = get_latest_occurrence(self.recipient_employee, row.penalty_type)
			if (
				latest
				and latest.period_start_date
				and getdate(latest.period_start_date) <= occurrence_date <= getdate(latest.period_lapse_date)
			):
				count = count_occurrences(
					self.recipient_employee, row.penalty_type, latest.period_start_date, latest.period_lapse_date
				)
				row.occurence_number = count + 1
				row.period_start_date = latest.period_start_date
				row.period_lapse_date = latest.period_lapse_date
			else:
				row.occurence_number = 1
				row.period_start_date = occurrence_date
				row.period_lapse_date = add_to_date(occurrence_date, years=1)

			levied, days = get_penalty_levied(min(cint(row.occurence_number), MAX_OCCURRENCE), row.penalty_type)
			row.penalty_levied = levied
			row.deduction = flt(days)


def get_latest_occurrence(employee, penalty_type):
	Penalty, Details = DocType("Penalty"), DocType("Penalty Issuance Details")
	rows = (
		frappe.qb.from_(Details)
		.join(Penalty).on(Details.parent == Penalty.name)
		.select(Details.period_start_date, Details.period_lapse_date)
		.where(
			(Details.parenttype == "Penalty")
			& (Details.penalty_type == penalty_type)
			& (Penalty.recipient_employee == employee)
			& (Penalty.workflow_state != "Penalty Rejected")
			& Details.period_start_date.isnotnull()
		)
		.orderby(Penalty.penalty_occurence_time, order=frappe.qb.desc)
		.orderby(Penalty.penalty_issuance_time, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=True)
	return rows[0] if rows else None


def count_occurrences(employee, penalty_type, start_date, lapse_date):
	Penalty, Details = DocType("Penalty"), DocType("Penalty Issuance Details")
	return len(
		(
			frappe.qb.from_(Details)
			.join(Penalty).on(Details.parent == Penalty.name)
			.select(Details.name)
			.where(
				(Details.parenttype == "Penalty")
				& (Details.penalty_type == penalty_type)
				& (Penalty.recipient_employee == employee)
				& (Penalty.workflow_state != "Penalty Rejected")
				& (Details.period_start_date == start_date)
				& (Details.period_lapse_date == lapse_date)
			)
		).run()
	)


def get_penalty_levied(occurrence, penalty_type):
	Matrix, PenaltyList = DocType("Penalty Details"), DocType("Penalty List")
	levied_field, days_field = f"occurence_type{occurrence}", f"occurence{occurrence}"
	rows = (
		frappe.qb.from_(Matrix)
		.join(PenaltyList).on(Matrix.parent == PenaltyList.name)
		.select(Matrix[levied_field], Matrix[days_field])
		.where((PenaltyList.active == 1) & (Matrix.penalty_description_english == penalty_type))
		.limit(1)
	).run()
	return rows[0] if rows else (None, 0)


@frappe.whitelist()
def get_permission_query_conditions(user):
	user_roles = frappe.get_roles(user)
	if user == "Administrator" or "Legal Manager" in user_roles:
		return ""
	else:
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"])
		if "Penalty Recipient" in user_roles and "Penalty Issuer" in user_roles:
			condition = '`tabPenalty`.`issuer_employee`="{employee}" or `tabPenalty`.`recipient_employee`="{employee}"'.format(employee = employee)
		elif "Penalty Issuer" in user_roles:
			condition = '`tabPenalty`.`issuer_employee`="{employee}"'.format(employee = employee)
		elif "Penalty Recipient" in user_roles:
			condition = '`tabPenalty`.`recipient_employee`="{employee}"'.format(employee = employee)
		else:
			condition = ""
		return condition

def has_permission():
	user_roles = frappe.get_roles(frappe.session.user)
	if frappe.session.user == "Administrator" or "Legal Manager" in user_roles or "Penalty Recipient" in user_roles or "Penalty Issuer" in user_roles:
		# dont allow non Administrator user to view / edit Administrator user
		return True
