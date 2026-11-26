# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# Records are created by the Initiate Penalty Issuance process, one per employee, and
# acknowledged from the mobile check-in screen.
class PenaltyAcknowledgement(Document):
	pass


def get_pending_penalty_notices(employee: str) -> list:
	"""Unacknowledged notices of submitted issuances for the employee, oldest first. No date limit."""
	ack = frappe.qb.DocType("Penalty Acknowledgement")
	issuance = frappe.qb.DocType("Penalty Issuance")
	return (
		frappe.qb.from_(ack)
		.join(issuance)
		.on(issuance.name == ack.penalty_issuance)
		.select(ack.name, ack.penalty_issuance, ack.issuer_name, ack.penalty_category, ack.penalty_occurence_time)
		.where(ack.employee == employee)
		.where(ack.acknowledged == 0)
		.where(issuance.docstatus == 1)
		.orderby(ack.penalty_occurence_time)
	).run(as_dict=True)
