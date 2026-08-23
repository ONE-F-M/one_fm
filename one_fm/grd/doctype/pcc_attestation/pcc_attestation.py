# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The attestation of an employee's Police Clearance Certificate (WI-002028).

Not to be confused with PCC Clearance, which is the recruitment-side record of obtaining
the certificate for a candidate abroad. This one tracks what happens to the certificate
once it is here: the embassy attests it, MOFA attests it, or it is translated - each step a
fee and a receipt the PRO has to produce before the file moves on.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

from one_fm.grd.utils import get_nationality_attestation_rule, get_pcc_attestation_fees

ATTESTATION = "Attestation"
TRANSLATION = "Translation"

DRAFT = "Draft"

# WI-002145: the three states "Assign PRO" hands the record to a PRO in. The fourth route
# out of Draft goes straight to the GR Operator - a nationality that needs no embassy, no
# MOFA and no translation has no PRO work to give anybody - so it is not gated on a PRO.
PRO_STATES = ("Pending Embassy", "Pending MOFA", "Pending Translation")

# WI-002029: the states the PRO holds the record in, and the receipt each one exists to
# collect. The workflow owns the transitions; this owns the rule that a state cannot be left
# until its receipt is attached, which is what every "blocks the state transition" criterion
# comes down to.
RECEIPT_REQUIRED_BY_STATE = {
	"Pending Embassy": ("upload_embassy_payment_receipt", "Upload Embassy Payment Receipt"),
	"Pending MOFA": ("upload_mofa_payment_receipt", "Upload MOFA Payment Receipt"),
	"Pending Translation": ("upload_translation_payment_receipt", "Upload Translation Payment Receipt"),
}

# Each receipt and the field that records when it went up. Read-only fields, stamped here
# rather than in the browser so the stamp is the server's clock and cannot be skipped by
# whatever attached the file.
RECEIPT_TIMESTAMPS = (
	("upload_embassy_payment_receipt", "upload_embassy_payment_receipt_on"),
	("upload_mofa_payment_receipt", "upload_mofa_payment_receipt_on"),
	("upload_translation_payment_receipt", "upload_translation_payment_receipt_on"),
)


def create_pcc_attestations(employee, category, preparation_name=None):
	"""Open the PCC records an overseas hire's nationality calls for (WI-002104).

	Always the attestation itself. A nationality whose row in the Nationality Attestation
	Rules has Translation Required ticked also gets a second, separate record for the
	translation - separate because the two are different pieces of work, done by different
	offices, each with its own fee and its own receipt, and the workflow routes them down
	different paths. One record carrying both would have to be in two states at once.

	A nationality with no row in the table needs no translation, which is the same answer
	the fee resolver gives it.
	"""
	rule = get_nationality_attestation_rule(employee.one_fm_nationality)

	records = [create_pcc_attestation(employee, category, preparation_name)]
	if rule and rule.translation_required:
		records.append(
			create_pcc_attestation(employee, category, preparation_name, attestation_type=TRANSLATION)
		)

	return records


def create_pcc_attestation(employee, category, preparation_name=None, attestation_type=ATTESTATION):
	"""Open a PCC record for an overseas hire (WI-002095).

	The requirements and the fees are not passed in: the controller derives them from the
	candidate's nationality on validate, so there is one place that reads the Nationality
	Attestation Rules and the caller cannot hand it a different answer.
	"""
	pcc = frappe.new_doc("PCC Attestation")
	pcc.employee = employee.name
	pcc.type = attestation_type
	pcc.category = category
	pcc.preparation = preparation_name
	pcc.insert()

	return pcc


class PCCAttestation(Document):
	def validate(self):
		self.set_attestation_requirements()
		self.set_receipt_timestamps()
		self.validate_receipt_for_state_being_left()
		self.validate_pro_user_before_assigning()

	def validate_pro_user_before_assigning(self):
		"""Refuse "Assign PRO" until there is a PRO to assign it to (WI-002145).

		The action names a person and the assignment rule for the three PRO states takes
		its assignee from `pro_user`, so without one the record moved to Pending Embassy,
		MOFA or Translation and sat there assigned to nobody - visible to no PRO and
		waiting on a receipt none of them knew was owed.

		Guarded on the state being left, read from the document as it was before this save,
		for the same reason the receipt check is: apply_workflow sets the destination on the
		document and then saves, so self.workflow_state is already the next state by the
		time validate runs.
		"""
		if self.is_new():
			return

		before_save = self.get_doc_before_save()
		if not before_save or before_save.get("workflow_state") != DRAFT:
			return

		if self.workflow_state not in PRO_STATES:
			return

		if self.pro_user:
			return

		frappe.throw(
			_("Please select a PRO User before proceeding."),
			title=_("PRO User Required"),
		)

	def on_update_after_submit(self):
		# The receipts are allow_on_submit, so a file can arrive after the record is
		# submitted. validate does not run on that path.
		self.set_receipt_timestamps()

	def set_attestation_requirements(self):
		"""Derive what this certificate needs from the candidate's nationality (WI-002025).

		The Nationality Attestation Rules in HR Settings say, per nationality, whether the
		embassy attests, whether MOFA attests, and whether the certificate has to be
		translated. All three are independent: the reporter's data has nationalities that need
		MOFA but no embassy, and one - Ugandan - that needs neither, only translation.

		Held on the record as three flags rather than inferred from the fees, because a fee of
		zero and a step that does not apply are different things, and the workflow routes on
		the difference. An embassy that attests for free still has to be visited.

		A nationality with no row in the table needs none of the three.

		The record's Type is handed to the resolver rather than applied afterwards, so there is
		one place that decides which fees apply: translation work never goes near an embassy or
		MOFA, and it carries the translation fee whatever the nationality's rule says.
		"""
		fees = get_pcc_attestation_fees(self.nationality, is_translation=self.type == TRANSLATION)

		self.embassy_attestation_required = int(fees.embassy_required)
		self.mofa_attestation_required = int(fees.mofa_required)
		self.translation_required = int(fees.translation_required)

		self.requires_embassy_attestation = fees.embassy_fee
		self.mofa_fee = fees.mofa_fee
		self.translation_fee = fees.translation_fee

	@property
	def needs_embassy_attestation(self):
		"""Does this candidate's nationality need the embassy step at all?

		Distinct from the fee being non-zero: an embassy that attests for free still has to be
		visited, so the question is what the rule says, not what it charges.
		"""
		return self.type == ATTESTATION and bool(self.embassy_attestation_required)

	@property
	def needs_mofa_attestation(self):
		"""Does this candidate's nationality need the MOFA step at all?

		The reason this exists: the reporter's data has a nationality that needs neither
		embassy nor MOFA, and routing "not embassy" straight to Pending MOFA would have
		blocked its PRO on a receipt that was never going to exist.
		"""
		return self.type == ATTESTATION and bool(self.mofa_attestation_required)

	def validate_receipt_for_state_being_left(self):
		"""Hold the record in a state until that state's receipt is attached (WI-002029).

		The PRO cannot hand a step back without evidence the fee was paid. Keyed on the state
		rather than on the action, because Pending MOFA and Pending Translation are both left
		by an action called "Submit" while Pending Embassy is left by "Submit MOFA Receipt",
		and because a state gains its meaning from the receipt it collects.

		The check is on the state being *left*, read from the document as it was before this
		save. `apply_workflow` sets the new state on the document and then saves it, so by the
		time validate runs `self.workflow_state` is already the destination - guarding on that
		would test the next step's receipt and let every transition through.

		There is no separate check for a non-attesting country: the workflow does not route one
		through Pending Embassy at all, so the state is unreachable for it.
		"""
		if self.is_new():
			return

		before_save = self.get_doc_before_save()
		if not before_save:
			return

		previous_state = before_save.get("workflow_state")
		if previous_state == self.workflow_state:
			return

		required = RECEIPT_REQUIRED_BY_STATE.get(previous_state)
		if not required:
			return

		fieldname, label = required
		if self.get(fieldname):
			return

		frappe.throw(
			_("{0} is required before this record can be submitted to the Government Relations Operator.")
			.format(frappe.bold(_(label))),
			title=_("Payment Receipt Required"),
		)

	def set_receipt_timestamps(self):
		"""Stamp when each receipt went up, and clear the stamp if the file is removed."""
		for receipt_field, timestamp_field in RECEIPT_TIMESTAMPS:
			has_receipt = bool(self.get(receipt_field))
			has_timestamp = bool(self.get(timestamp_field))

			if has_receipt and not has_timestamp:
				self.set_field(timestamp_field, now())
			elif not has_receipt and has_timestamp:
				self.set_field(timestamp_field, None)

	def set_field(self, fieldname, value):
		"""Write a field on either side of submit.

		After submit the row is already saved, so an assignment in
		`on_update_after_submit` would be thrown away.
		"""
		if self.docstatus == 1:
			self.db_set(fieldname, value)
		else:
			self.set(fieldname, value)
