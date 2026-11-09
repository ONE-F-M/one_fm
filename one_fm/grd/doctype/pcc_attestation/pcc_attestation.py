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

from one_fm.grd.utils import get_nationality_attestation_rule, get_pcc_attestation_fees

ATTESTATION = "Attestation"
TRANSLATION = "Translation"

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
		# The PCC Attestation Lifecycle process checks the PRO User and each state's
		# payment receipt in its script tasks before it moves the record on.
		self.set_attestation_requirements()

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
