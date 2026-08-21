"""
WI-002106: the Server Scripts that took over Visa Request's mandatory-field validations
when they left the controller.

The scripts themselves are authored in the Processa editor and moved between sites by
export/import, so the site's ``Server Script`` records are what actually runs. The
bodies are mirrored here so they get reviewed with the code they replaced, and
``TestTheSiteMatchesTheReviewedBodies`` fails if the two drift apart - editing a script
in the editor without updating this file is exactly how the reviewed version stops
being the running version.

The behaviour tests exercise the literals below rather than the site records, so they
give the same answer on a site where the import has not run yet.

What the engine does with these, and what the tests therefore mirror: it builds a
namespace of ``frappe`` / ``doc`` / ``task_data`` / ``result`` and calls plain ``exec()``
on the body, having first put it through the BPMN script security gate.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_bpmn.security.script_validator import deep_inspect_script

# ═══════════════════════════════════════════════════════════════════════════════
# The script bodies, and the script task each one belongs to.
# ═══════════════════════════════════════════════════════════════════════════════
#
# Every one re-checks its own condition instead of trusting the gateway that routed to
# it. All of these gateways currently have branches with no condition and no default
# flow, so a complete document can be sent down the failure branch; a script that only
# threw would then block a request that is perfectly valid. Re-checking makes each
# script correct whichever way the gateway sends it, and the ``result`` key it sets
# gives the gateway a real variable to route on once the conditions are written.

# AC 7 — replaces VisaRequest.validate_references().
#
# Note for whoever wires this up: the gateway ahead of this task was renamed to "Is Visa
# & Payment Receipt Attached?", so on its own it no longer covers the Visa Reference
# Number the AC also requires. This script checks all three, which is what makes it safe
# for the Python to have gone.
VISA_DETAILS_SCRIPT = '''# WI-002106 / AC 7: the visa reference, the payment receipt and the visa document
# are all required before a Visa Request may be submitted to the recruiter.
#
# Re-checked here rather than taken on trust from the gateway, so a request that is
# actually complete is not blocked if it is routed down this branch by mistake.
REQUIRED = (
	("visa_reference_number", "Visa Reference Number"),
	("payment_receipt", "Payment Receipt"),
	("visa_document", "Visa Document"),
)

missing = [label for fieldname, label in REQUIRED if not doc.get(fieldname)]

# Given to the gateway so it can route on a real value instead of reading document
# fields it cannot see.
result["visa_details_complete"] = not missing

if missing:
	frappe.throw(
		"The following are required before submitting to the recruiter: {0}".format(
			", ".join(missing)
		),
		title="Missing Required Fields",
	)
'''

# AC 6. The reason list is not repeated here: moi_rejection_remark is already a Select,
# so the field itself is the one source of truth for what is offered. Duplicating the
# options in a script is how the two drift apart.
MOI_REJECTION_REASON_SCRIPT = '''# WI-002106 / AC 6: an MOI rejection must record which of the reasons applied.
# The options live on moi_rejection_remark itself, so this only checks that one was
# chosen - the field rejects anything outside its own list on save.
reason = (doc.get("moi_rejection_remark") or "").strip()

result["moi_rejection_reason_set"] = bool(reason)

if not reason:
	frappe.throw(
		"Select a reason for the MOI rejection before proceeding.",
		title="MOI Rejection Reason Required",
	)
'''

# No AC names this one, but the diagram does and nothing about it is open: the three
# fields are the ones its own gateway condition already names, and all three exist.
#
# The controller's PAM Reference Number check is NOT removed alongside this. That check
# guards a different moment - the way out of Pending By PAM - and until the process
# owner says which stage is authoritative, dropping it would leave that transition
# unguarded.
PAM_DETAILS_SCRIPT = '''# WI-002106: the PAM details a GRD Operator has to record before a Visa Request can go
# to the GRD Manager - the PAM file, the reference number PAM issued, and the
# designation taken from the PAM designation list.
#
# The three fields are the ones the diagram's own gateway condition names.
REQUIRED = (
	("custom_pam_file", "PAM File"),
	("pam_reference_number", "PAM Reference Number"),
	("custom_pam_designation_list", "PAM Designation List"),
)

missing = [label for fieldname, label in REQUIRED if not doc.get(fieldname)]

result["pam_details_complete"] = not missing

if missing:
	frappe.throw(
		"The following PAM details are required before submitting to the GRD Manager: {0}".format(
			", ".join(missing)
		),
		title="PAM Details Required",
	)
'''

# No AC names this one either, and there is no controller code to remove with it: no
# backend validation ever covered the work permit number. The rule is new with the map.
WORK_PERMIT_NUMBER_SCRIPT = '''# WI-002106: a PAM approval is only complete once the work permit number PAM issued has
# been recorded on the Visa Request.
work_permit_number = (doc.get("custom_work_permit_number") or "").strip()

result["work_permit_number_set"] = bool(work_permit_number)

if not work_permit_number:
	frappe.throw(
		"Enter the Work Permit Number issued by PAM before proceeding.",
		title="Work Permit Number Required",
	)
'''

# Replaces the 'Pending by GRD Operator' branch of the client-side rejection dialog.
OPERATOR_REJECTION_REASON_SCRIPT = '''# WI-002106: a GRD Operator rejection has to say why - the recruiter is being asked to
# correct something and cannot act on a bare rejection.
#
# Note for whoever writes this gateway's conditions: the "No" branch currently tests
# pam_remarks, which is a PAM details field and has nothing to do with an operator
# rejection. The reason is stored in operator_rejection_remark.
reason = (doc.get("operator_rejection_remark") or "").strip()

result["operator_rejection_reason_set"] = bool(reason)

if not reason:
	frappe.throw(
		"Enter a reason for rejecting this Visa Request before proceeding.",
		title="Rejection Reason Required",
	)
'''

# Replaces the 'Pending GRD Manager Approval' branch of the same dialog.
MANAGER_REJECTION_REASON_SCRIPT = '''# WI-002106: a GRD Manager rejection has to say why - it sends the request back to the
# GRD Operator, who needs to know what to change.
reason = (doc.get("grd_manager_remark") or "").strip()

result["manager_rejection_reason_set"] = bool(reason)

if not reason:
	frappe.throw(
		"Enter a reason for rejecting this Visa Request before proceeding.",
		title="Rejection Reason Required",
	)
'''

# (script name, BPMN script task id, task label on the canvas, body)
#
# Names are the ones actually on the site - they follow each shape's own label rather
# than the "... Are Mandatory" convention proposed while drafting.
#
# Only four of the six drafted bodies made it in. The two rejection-reason scripts for
# the GRD Manager and MOI shapes are not here because they do not exist yet, and the
# reason is worth understanding before adding them:
#
# ``_extract_script_task_config`` falls back to reading a script task's inline
# ``<bpmn:script>`` text as a Server Script NAME whenever the task carries no
# ``serverScript`` attribute and the inline text does not look like Python. Four shapes
# carry the inline text "Require Rejection Reason" - the operator, manager, MOI and PAM
# details tasks - so a single Server Script by that name silently binds to all four,
# and three of them then check operator_rejection_remark, which is not their field.
#
# So the manager and MOI scripts cannot simply be added under a shared name. Each shape
# needs its own name AND an explicit serverScript attribute. Until then the client-side
# dialog keeps handling those two states - see visa_request.js.
SCRIPTS = (
	(
		"Visa Details Section is Mandatory",
		"Activity_0y674id",
		"Visa Details Section is Mandatory",
		VISA_DETAILS_SCRIPT,
	),
	(
		"PAM Details is Mandatory",
		"Activity_0r9epyv",
		"PAM Details is Mandatory",
		PAM_DETAILS_SCRIPT,
	),
	(
		"Work Permit Number is Mandatory",
		"Activity_1y06wft",
		"Work Permit Number is Mandatory",
		WORK_PERMIT_NUMBER_SCRIPT,
	),
	(
		"Require Rejection Reason",
		"Activity_0sa0xb3",
		"Require Rejection Reason",
		OPERATOR_REJECTION_REASON_SCRIPT,
	),
)

# Drafted, reviewed, and deliberately not on the site yet. Kept here so the bodies are
# not rewritten from scratch once each shape has a distinct name and an explicit
# serverScript attribute; add them to SCRIPTS at that point.
PENDING_SCRIPTS = (
	("MOI Rejection Reason is Mandatory", "Activity_0dtjaug", MOI_REJECTION_REASON_SCRIPT),
	("GRD Manager Rejection Reason is Mandatory", "Activity_0nxcbzb", MANAGER_REJECTION_REASON_SCRIPT),
)


def run_script(body: str, **fields) -> dict:
	"""Execute a BPMN Server Script body the way FrappeScriptEngine does.

	One namespace for globals and locals, ``doc`` pre-loaded, ``result`` pre-set to {} -
	mirrors ``FrappeScriptEngine._run_frappe_server_script``. Returns ``result``.
	"""
	result = {}
	namespace = {
		"frappe": frappe,
		"__builtins__": __builtins__,
		"doc": frappe._dict(fields),
		"result": result,
		"task_data": {},
		"context_doctype": "Visa Request",
		"context_docname": "VR-TEST-00001",
	}
	exec(body, namespace)  # noqa: S102
	return result


def missing_from_site() -> list:
	return [name for name, _id, _label, _body in SCRIPTS if not frappe.db.exists("Server Script", name)]


class TestTheScriptsPassTheSecurityGate(FrappeTestCase):
	"""Every BPMN script task body is gated on save and again at deploy. A body that
	fails the gate cannot be attached to the diagram at all, so this comes first."""

	# The pending two are gated as well: they are reviewed here, so they should be known
	# to pass before anyone pastes them in.
	ALL_BODIES = tuple((name, body) for name, _id, _label, body in SCRIPTS) + tuple(
		(name, body) for name, _id, body in PENDING_SCRIPTS
	)

	def test_no_violations_in_any_body(self):
		for name, body in self.ALL_BODIES:
			with self.subTest(script=name):
				self.assertEqual(deep_inspect_script(body), [], msg=name)

	def test_each_body_compiles_in_the_restricted_context(self):
		# Server Script.validate() runs the body through RestrictedPython and msgprints
		# any failure as a "Compilation warning". BPMN scripts execute through plain
		# exec(), so a warning would not stop them running - but it would greet whoever
		# opens the script, so it is worth not having.
		from RestrictedPython import compile_restricted

		from frappe.utils.safe_exec import FrappeTransformer

		for name, body in self.ALL_BODIES:
			with self.subTest(script=name):
				compile_restricted(body, policy=FrappeTransformer)

	def test_every_script_targets_a_distinct_task(self):
		# Four shapes are all labelled "Require Rejection Reason", so the ids are the
		# only thing telling them apart. A duplicate here means two rules were pointed
		# at one shape and one of them is not running.
		ids = [task_id for _name, task_id, _label, _body in SCRIPTS] + [
			task_id for _name, task_id, _body in PENDING_SCRIPTS
		]
		self.assertEqual(len(ids), len(set(ids)))

		names = [name for name, _id, _label, _body in SCRIPTS] + [
			name for name, _id, _body in PENDING_SCRIPTS
		]
		self.assertEqual(len(names), len(set(names)))


class TestTheSiteMatchesTheReviewedBodies(FrappeTestCase):
	"""The scripts are authored in the editor, so the site is what runs. This is the
	guard against the running version quietly diverging from the reviewed one."""

	def test_every_script_exists_on_this_site(self):
		absent = missing_from_site()
		self.assertEqual(
			absent,
			[],
			msg=(
				f"Not imported yet: {', '.join(absent)}. Paste each body into its script "
				"task's Server Script field in the Processa editor, then export/import."
			),
		)

	def test_no_script_has_drifted_from_the_body_reviewed_here(self):
		for name, _id, _label, body in SCRIPTS:
			if not frappe.db.exists("Server Script", name):
				continue
			with self.subTest(script=name):
				on_site = frappe.db.get_value("Server Script", name, "script") or ""
				self.assertEqual(on_site.strip(), body.strip(), msg=name)

	def test_none_of_them_is_disabled(self):
		# A disabled script is logged and skipped at runtime, so the rule silently
		# stops applying rather than failing.
		for name, _id, _label, _body in SCRIPTS:
			if not frappe.db.exists("Server Script", name):
				continue
			with self.subTest(script=name):
				self.assertFalse(frappe.db.get_value("Server Script", name, "disabled"), msg=name)


COMPLETE_VISA_DETAILS = {
	"visa_reference_number": "VISA-9001",
	"payment_receipt": "/private/files/receipt.pdf",
	"visa_document": "/private/files/visa.pdf",
}

COMPLETE_PAM_DETAILS = {
	"custom_pam_file": "PAM-FILE-001",
	"pam_reference_number": "PAM-9001",
	"custom_pam_designation_list": "PAM-DESIG-001",
}

BLANKS = (None, "", "   ", "\n")


class TestVisaDetailsAreMandatory(FrappeTestCase):
	"""AC 7: the visa reference, payment receipt and visa document are all required
	before a Visa Request may be submitted to the recruiter."""

	def test_a_complete_request_passes_and_says_so(self):
		result = run_script(VISA_DETAILS_SCRIPT, **COMPLETE_VISA_DETAILS)
		self.assertTrue(result["visa_details_complete"])

	def test_each_missing_field_on_its_own_is_refused(self):
		for fieldname in COMPLETE_VISA_DETAILS:
			fields = dict(COMPLETE_VISA_DETAILS, **{fieldname: None})
			with self.subTest(missing=fieldname):
				with self.assertRaises(frappe.ValidationError):
					run_script(VISA_DETAILS_SCRIPT, **fields)

	def test_the_message_names_every_field_that_is_missing(self):
		# The operator should not have to submit three times to discover three gaps.
		with self.assertRaises(frappe.ValidationError) as caught:
			run_script(VISA_DETAILS_SCRIPT)

		message = str(caught.exception)
		for label in ("Visa Reference Number", "Payment Receipt", "Visa Document"):
			self.assertIn(label, message, msg=label)

	def test_an_empty_string_counts_as_missing(self):
		# An Attach field cleared in the UI can land as "" rather than None.
		fields = dict(COMPLETE_VISA_DETAILS, visa_reference_number="")
		with self.assertRaises(frappe.ValidationError):
			run_script(VISA_DETAILS_SCRIPT, **fields)


class TestPamDetailsAreMandatory(FrappeTestCase):
	"""The PAM file, reference number and designation the GRD Operator records before
	the request goes to the GRD Manager."""

	def test_a_complete_request_passes_and_says_so(self):
		result = run_script(PAM_DETAILS_SCRIPT, **COMPLETE_PAM_DETAILS)
		self.assertTrue(result["pam_details_complete"])

	def test_each_missing_field_on_its_own_is_refused(self):
		for fieldname in COMPLETE_PAM_DETAILS:
			fields = dict(COMPLETE_PAM_DETAILS, **{fieldname: None})
			with self.subTest(missing=fieldname):
				with self.assertRaises(frappe.ValidationError):
					run_script(PAM_DETAILS_SCRIPT, **fields)

	def test_all_three_are_required_not_merely_one_of_them(self):
		# The diagram's own gateway spells the "Yes" branch as an AND of all three, but
		# writes the "No" branch as an OR - so a request with one field set would pass
		# both. The script is the AND.
		with self.assertRaises(frappe.ValidationError) as caught:
			run_script(PAM_DETAILS_SCRIPT, pam_reference_number="PAM-9001")

		message = str(caught.exception)
		self.assertIn("PAM File", message)
		self.assertIn("PAM Designation List", message)
		self.assertNotIn("PAM Reference Number", message)


class TestWorkPermitNumberIsMandatory(FrappeTestCase):
	"""A PAM approval is only complete once the work permit number is recorded."""

	def test_a_number_passes_and_says_so(self):
		result = run_script(WORK_PERMIT_NUMBER_SCRIPT, custom_work_permit_number="WP-4471")
		self.assertTrue(result["work_permit_number_set"])

	def test_a_blank_is_refused(self):
		for blank in BLANKS:
			with self.subTest(value=repr(blank)):
				with self.assertRaises(frappe.ValidationError):
					run_script(WORK_PERMIT_NUMBER_SCRIPT, custom_work_permit_number=blank)


class TestTheRejectionReasonScripts(FrappeTestCase):
	"""Three near-identical rules, each reading the field its own stage writes. They are
	tested together because the risk they share is pointing at the wrong field."""

	CASES = (
		(OPERATOR_REJECTION_REASON_SCRIPT, "operator_rejection_remark", "operator_rejection_reason_set"),
		(MANAGER_REJECTION_REASON_SCRIPT, "grd_manager_remark", "manager_rejection_reason_set"),
		(MOI_REJECTION_REASON_SCRIPT, "moi_rejection_remark", "moi_rejection_reason_set"),
	)

	def test_a_reason_passes_and_says_so(self):
		for body, fieldname, result_key in self.CASES:
			with self.subTest(field=fieldname):
				result = run_script(body, **{fieldname: "Because the passport is short-dated"})
				self.assertTrue(result[result_key])

	def test_a_blank_is_refused(self):
		# The Select's own blank option comes through as "", and a stray space would
		# otherwise satisfy a plain truthiness check.
		for body, fieldname, _result_key in self.CASES:
			for blank in BLANKS:
				with self.subTest(field=fieldname, value=repr(blank)):
					with self.assertRaises(frappe.ValidationError):
						run_script(body, **{fieldname: blank})

	def test_each_reads_only_its_own_field(self):
		# A rejection reason recorded at one stage must not satisfy another stage's
		# check - which is what a copy-paste between these three would cause.
		for body, fieldname, _result_key in self.CASES:
			others = {f: "set at another stage" for _b, f, _k in self.CASES if f != fieldname}
			with self.subTest(field=fieldname):
				with self.assertRaises(frappe.ValidationError):
					run_script(body, **others)


class TestTheMoiReasonListIsNotDuplicated(FrappeTestCase):
	def test_every_option_the_field_offers_is_accepted(self):
		# The options live on moi_rejection_remark. Repeating them in the script is how
		# the two drift apart, so the script must accept whatever the field accepts.
		options = frappe.get_meta("Visa Request").get_field("moi_rejection_remark").options or ""
		for option in [o for o in options.split("\n") if o.strip()]:
			with self.subTest(option=option):
				result = run_script(MOI_REJECTION_REASON_SCRIPT, moi_rejection_remark=option)
				self.assertTrue(result["moi_rejection_reason_set"])


class TestTheControllerNoLongerDoesThisWork(FrappeTestCase):
	"""The other half of the migration: the code these scripts replaced is gone, and the
	checks that are still blocked on a decision are still there."""

	def test_validate_references_is_gone(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import VisaRequest

		self.assertFalse(hasattr(VisaRequest, "validate_references"))

	def test_the_moi_reference_check_is_gone_but_the_pam_one_stays(self):
		import inspect

		from one_fm.visa_management.doctype.visa_request.visa_request import VisaRequest

		source = inspect.getsource(VisaRequest.validate_workflow_transitions)
		self.assertNotIn("moi_reference_number", source)
		self.assertIn("pam_reference_number", source)

	def test_the_client_script_no_longer_prompts_for_the_operator_rejection_reason(self):
		# The one rejection state whose script is on the site and resolves to the right
		# field. The manager and MOI states still prompt here on purpose - see the note
		# on SCRIPTS above and in visa_request.js.
		self.assertEqual(
			self.handled_rejection_states(),
			["Pending GRD Manager Approval", "Pending By PAM", "Pending By MOI"],
		)

	def test_every_state_the_dialog_still_handles_knows_where_to_store_the_reason(self):
		# Falling through to the 'rejection_remarks' default would write a field that
		# does not exist on Visa Request, losing the reason silently.
		import re

		source = self.client_script()
		block = re.search(r"REJECTION_REMARK_FIELD_BY_STATE = \{(.*?)\n\};", source, re.S)
		self.assertIsNotNone(block, msg="the remark-field map no longer parses - update this test")
		mapped = dict(re.findall(r"'([^']+)':\s*'([^']+)'", block.group(1)))

		meta = frappe.get_meta("Visa Request")
		for state in self.handled_rejection_states():
			with self.subTest(state=state):
				self.assertIn(state, mapped)
				self.assertIsNotNone(meta.get_field(mapped[state]), msg=mapped[state])

	@staticmethod
	def client_script() -> str:
		import pathlib

		return (
			pathlib.Path(frappe.get_app_path("one_fm"))
			/ "visa_management"
			/ "doctype"
			/ "visa_request"
			/ "visa_request.js"
		).read_text()

	@classmethod
	def handled_rejection_states(cls) -> list:
		"""The dialog's own list of states - not any mention of them in a comment."""
		import re

		block = re.search(r"const handledStates = \[(.*?)\]", cls.client_script(), re.S)
		if block is None:
			raise AssertionError("handledStates no longer parses - update this test")
		return re.findall(r"'([^']+)'", block.group(1))
