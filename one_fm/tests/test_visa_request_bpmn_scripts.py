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

# AC 3 — replaces the 'Pending By PAM' branch of the client-side rejection dialog, and
# the hardcoded reason list that branch offered.
#
# The list moved onto pam_rejection_remark, which is now the Select the AC calls a
# dropdown, with pam_rejection_remarks beside it for the free text. Both fields had to
# become writable: the dialog wrote the reason with frm.set_value, which a read-only field
# allows, and typing it on the form does not.
#
# The reason is required, the remarks are not. The AC makes only the dropdown mandatory,
# and a reason from a fixed list is what the process acts on - REAPPLY_REASONS in
# visa_request.py reads exactly this field to decide whether a fresh attempt is worth
# making.
PAM_REJECTION_REASON_SCRIPT = '''# WI-002106 / AC 3: a PAM rejection must record which of the reasons applied, and the
# remarks that go with it are kept alongside.
#
# The options live on pam_rejection_remark itself, so this only checks that one was
# chosen - the field rejects anything outside its own list on save. Two fieldnames one
# letter apart, so worth spelling out: pam_rejection_remark is the reason, and
# pam_rejection_remarks is the free text.
reason = (doc.get("pam_rejection_remark") or "").strip()
remarks = (doc.get("pam_rejection_remarks") or "").strip()

result["pam_rejection_reason_set"] = bool(reason)
result["pam_rejection_reason"] = reason
result["pam_rejection_remarks"] = remarks

if not reason:
	frappe.throw(
		"Select a reason for the PAM rejection before proceeding.",
		title="PAM Rejection Reason Required",
	)
'''

# AC 8 — replaces queue_document_ocr() and the on_update trigger it fired from.
#
# The reading itself stays in the app. A Server Script is the wrong place for the Mindee
# models, the field maps and the attachment paths: they are covered by
# test_visa_document_ocr.py, and a copy in here is how the two would drift. What the work
# item asked to move is when the reading happens, which is all this does.
OCR_SCRIPT = '''# WI-002106 / AC 8: read the visa copy and the payment receipt attached at Pending Visa
# Issuance, and write what they say to the request - the visa number, its issue and expiry
# dates, and the payment date and time.
#
# Runs inline rather than enqueued: the next task hands the request to the recruiter, so
# the values have to be on it by then. run_document_ocr logs and skips a document it
# cannot read, so a Mindee outage cannot strand a visa here.
read_documents = frappe.get_attr(
	"one_fm.visa_management.doctype.visa_request.visa_request.run_document_ocr"
)

extracted = read_documents(doc.name)

# Reported so a gateway can route on what was actually filled instead of assuming the
# read succeeded.
result["ocr_fields_filled"] = sorted(extracted)
result["ocr_read_anything"] = bool(extracted)
'''

# WI-002152 / WI-002106 AC 4 — the step the "Reapply for Visa" message runs.
#
# It sits in the event subprocess Activity_0rmnc4c, whose start event Event_1hlw0sb is a
# message start with no messageRef. SpiffWorkflow falls back to the start event's own name
# for the message name in that case, so the message is "Reapply for Visa" and correlation
# is by that string alone - renaming the shape stops the button working, silently.
#
# The raising itself stays in reapply_visa_request(): the -1 naming, the fields that must
# not carry over, and the permission checks are all already there and already tested. A
# copy in here is a second opinion about what a reapplication is, which is exactly what
# this work item is removing.
REAPPLY_SCRIPT = '''# WI-002152: the "Reapply for Visa" message the Reapply Visa button sends arrives here,
# and this raises the fresh Visa Request - named <original>-1, carrying the application
# without the outcome of the attempt that failed.
#
# Checked before raising rather than after: a message can arrive more than once (a double
# click, a redelivery), and each arrival runs this step again. reapply_visa_request would
# throw on the second, which fails the whole instance - so the repeat is reported as a
# no-op instead.
module = "one_fm.visa_management.doctype.visa_request.visa_request."

already = frappe.get_attr(module + "existing_reapplication")(doc.name)

if already:
	result["reapplication"] = already
	result["created"] = False
else:
	raised = frappe.get_attr(module + "reapply_visa_request")(doc.name)
	result["reapplication"] = raised["name"]
	result["created"] = True

result["reapplied_from"] = doc.name
'''

# (script name, BPMN script task id, task label on the canvas, body)
#
# Each script is named after its own shape, and no two shapes share a name. That is not
# cosmetic - it is what stops the compiler's fallback mis-binding them.
#
# ``_extract_script_task_config`` reads a script task's inline ``<bpmn:script>`` text as
# a Server Script NAME whenever the task carries no ``serverScript`` attribute and the
# text does not look like Python. Four shapes used to be labelled "Require Rejection
# Reason" and carried that text inline - the operator, GRD Manager, MOI and PAM-details
# tasks - so one Server Script by that name bound to all four, and three of them then
# checked operator_rejection_remark, which is not their field. The PAM-details shape was
# running the operator's check entirely.
#
# Two rules follow from that, and both matter when adding the next script:
#   1. Give every shape a distinct label, and name its script the same.
#   2. Set the ``serverScript`` attribute explicitly. The attribute wins over the inline
#      text, so an explicit binding cannot be hijacked by a stale label.
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
		"Operator Rejection Reason",
		"Activity_0sa0xb3",
		"Operator Rejection Reason",
		OPERATOR_REJECTION_REASON_SCRIPT,
	),
	(
		"MOI Rejection Reason",
		"Activity_0dtjaug",
		"MOI Rejection Reason",
		MOI_REJECTION_REASON_SCRIPT,
	),
	(
		"GRD Manager Rejection Reason",
		"Activity_0nxcbzb",
		"GRD Manager Rejection Reason",
		MANAGER_REJECTION_REASON_SCRIPT,
	),
)

# Drafted and reviewed here, not on the site yet - each one is pasted into its shape's
# Server Script field in the editor and comes across by export/import. Move it into
# SCRIPTS once it exists and its shape carries the matching serverScript attribute; the
# drift guard below only covers what is in SCRIPTS.
PENDING_SCRIPTS = (
	("PAM Rejection Reason", "Activity_1pgghs6", PAM_REJECTION_REASON_SCRIPT),
	(
		"Auto Fetch Visa & payment Details using OCR",
		"Activity_0ljbcgg",
		OCR_SCRIPT,
	),
	("Create new visa request version", "Activity_0s8jngv", REAPPLY_SCRIPT),
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


class TestTheDiagramBindsEachScriptToItsOwnShape(FrappeTestCase):
	"""The other half of the drift guard. TestTheSiteMatchesTheReviewedBodies proves the
	script bodies are the reviewed ones; this proves each one is attached to the shape it
	was written for.

	Worth its own test because picking the wrong script in the editor's dropdown is silent:
	an exclusive gateway routes to the shape, the shape runs somebody else's rule, and the
	rule that shape exists for is simply never applied. It happened - Activity_1pgghs6
	("PAM Rejection Reason") was bound to the OCR script, so a PAM rejection ran an
	attachment read and never asked for a reason.
	"""

	PROCESS_NAME = "Visa"

	def bindings(self) -> dict:
		"""{script task id: bound Server Script name} from the Visa model on this site."""
		import xml.etree.ElementTree as ET

		model = frappe.db.get_value(
			"BPMN Process Model", {"process_name": self.PROCESS_NAME}, ["name", "bpmn_xml"], as_dict=True
		)
		if not model or not model.bpmn_xml:
			self.skipTest(f"No {self.PROCESS_NAME} BPMN Process Model on this site")

		bpmn = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
		spiff = "{http://spiffworkflow.org/bpmn/schema/1.0/core}"
		root = ET.fromstring(model.bpmn_xml.strip().encode("utf-8"))

		# The attribute only. The compiler does fall back to the inline <bpmn:script> text
		# when the attribute is absent, but that fallback is what mis-bound four shapes to
		# one script before - so an explicit attribute is the thing being asserted here.
		return {
			elem.get("id"): elem.get(spiff + "serverScript", "").strip()
			for elem in root.iter(bpmn + "scriptTask")
		}

	def test_every_script_is_bound_to_the_task_it_was_written_for(self):
		bound = self.bindings()
		expected = [(name, task_id) for name, task_id, _label, _body in SCRIPTS] + [
			(name, task_id) for name, task_id, _body in PENDING_SCRIPTS
		]

		for name, task_id in expected:
			with self.subTest(script=name, task=task_id):
				self.assertIn(task_id, bound, msg=f"{task_id} is not a script task on the diagram")
				self.assertEqual(bound[task_id], name)

	def test_no_script_task_on_the_diagram_is_left_unbound(self):
		# An unbound script task is not a compile error - it silently does nothing, so the
		# rule looks implemented on the canvas and is not applied.
		unbound = [task_id for task_id, script in self.bindings().items() if not script]

		self.assertEqual(unbound, [])


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


class TestThePamRejectionReasonScript(FrappeTestCase):
	"""AC 3: the reason is a dropdown and it is mandatory; the remarks beside it are
	stored but not demanded."""

	REASON = "Worker is in Black List"

	def test_a_reason_passes_and_reports_itself(self):
		result = run_script(PAM_REJECTION_REASON_SCRIPT, pam_rejection_remark=self.REASON)

		self.assertTrue(result["pam_rejection_reason_set"])
		self.assertEqual(result["pam_rejection_reason"], self.REASON)

	def test_a_blank_reason_is_refused(self):
		for blank in BLANKS:
			with self.subTest(value=repr(blank)):
				with self.assertRaises(frappe.ValidationError):
					run_script(PAM_REJECTION_REASON_SCRIPT, pam_rejection_remark=blank)

	def test_the_remarks_are_carried_but_not_demanded(self):
		result = run_script(
			PAM_REJECTION_REASON_SCRIPT,
			pam_rejection_remark=self.REASON,
			pam_rejection_remarks="File 88213, checked with PAM on the 4th",
		)

		self.assertEqual(result["pam_rejection_remarks"], "File 88213, checked with PAM on the 4th")

	def test_remarks_on_their_own_do_not_satisfy_the_reason(self):
		# The AC makes the dropdown mandatory. Free text in the box beside it is not a
		# reason the process can act on - see the reapply gate.
		with self.assertRaises(frappe.ValidationError):
			run_script(PAM_REJECTION_REASON_SCRIPT, pam_rejection_remarks="rejected, see email")

	def test_it_does_not_read_another_stage_s_reason(self):
		with self.assertRaises(frappe.ValidationError):
			run_script(
				PAM_REJECTION_REASON_SCRIPT,
				moi_rejection_remark="set at another stage",
				grd_manager_remark="set at another stage",
				operator_rejection_remark="set at another stage",
			)


class TestThePamReasonListLivesOnTheField(FrappeTestCase):
	"""AC 3 moved the list out of the client script and onto pam_rejection_remark. These
	are the properties that made that safe to do."""

	def field(self):
		return frappe.get_meta("Visa Request").get_field("pam_rejection_remark")

	def options(self):
		return [o for o in (self.field().options or "").split("\n") if o.strip()]

	def test_the_reason_is_a_dropdown(self):
		self.assertEqual(self.field().fieldtype, "Select")

	def test_the_reason_can_be_typed_on_the_form(self):
		# The dialog wrote it with frm.set_value, which a read-only field allows. Now that
		# the map asks for it on the form, read-only would leave the task unpassable.
		self.assertFalse(self.field().read_only)

	def test_the_remarks_are_a_separate_writable_field(self):
		remarks = frappe.get_meta("Visa Request").get_field("pam_rejection_remarks")

		self.assertIsNotNone(remarks)
		self.assertFalse(remarks.read_only)
		self.assertNotEqual(remarks.fieldname, self.field().fieldname)

	def test_every_option_the_field_offers_is_accepted(self):
		for option in self.options():
			with self.subTest(option=option):
				result = run_script(PAM_REJECTION_REASON_SCRIPT, pam_rejection_remark=option)
				self.assertTrue(result["pam_rejection_reason_set"])

	def test_both_reapply_reasons_are_still_offered(self):
		# The Reapply Visa button and reapply_visa_request() both gate on this field
		# holding one of REAPPLY_REASONS. A reason dropped from the options - or reworded
		# in it - takes reapplication with it, silently.
		from one_fm.visa_management.doctype.visa_request.visa_request import REAPPLY_REASONS

		for reason in REAPPLY_REASONS:
			with self.subTest(reason=reason):
				self.assertIn(reason, self.options())

	def test_the_options_the_dialog_used_to_offer_are_all_still_there(self):
		# Every value already recorded on this site came from that list, and the field
		# refuses anything outside its options on save.
		for reason in (
			"Passport Validity is Less than 18 Months",
			"Worker's age is below the legal minimum",
			"The worker's gender does not match the profession",
			"The occupation requires amendment to specify the worker's specialization",
			"An active file exists for this worker",
			"Worker is in Black List",
		):
			with self.subTest(reason=reason):
				self.assertIn(reason, self.options())

	def test_a_reapplication_does_not_carry_the_rejection_over(self):
		from one_fm.visa_management.doctype.visa_request.visa_request import OUTCOME_FIELDS

		self.assertIn("pam_rejection_remark", OUTCOME_FIELDS)
		self.assertIn("pam_rejection_remarks", OUTCOME_FIELDS)


class TestTheOcrScript(FrappeTestCase):
	"""AC 8: the step that reads the visa copy and the payment receipt. Mindee is not
	called - the extraction itself is covered by test_visa_document_ocr.py."""

	VISA_REQUEST = "VR-TEST-00001"

	def run_with(self, extracted):
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request import visa_request as module

		calls = []

		def fake_read(name):
			calls.append(name)
			return extracted

		with patch.object(module, "run_document_ocr", fake_read):
			result = run_script(OCR_SCRIPT, name=self.VISA_REQUEST)

		return result, calls

	def test_it_reads_the_request_the_task_is_running_on(self):
		_result, calls = self.run_with({})

		self.assertEqual(calls, [self.VISA_REQUEST])

	def test_it_reports_which_fields_the_documents_filled(self):
		result, _calls = self.run_with(
			{
				"visa_reference_number": "283059338",
				"visa_issue_date": "2026-01-19",
				"visa_expiry_date": "2026-04-18",
				"payment_date": "2026-01-19 19:36:05",
			}
		)

		self.assertTrue(result["ocr_read_anything"])
		self.assertEqual(
			result["ocr_fields_filled"],
			["payment_date", "visa_expiry_date", "visa_issue_date", "visa_reference_number"],
		)

	def test_an_unreadable_document_is_reported_rather_than_raised(self):
		# run_document_ocr logs and returns nothing. The step still completes: a Mindee
		# outage must not strand a visa, and the operator can key the values in.
		result, _calls = self.run_with({})

		self.assertFalse(result["ocr_read_anything"])
		self.assertEqual(result["ocr_fields_filled"], [])

	def test_it_asks_for_every_field_the_work_item_named(self):
		# AC 8 names the visa number, its two dates, and the payment date and time. They
		# are the OCR_DOCUMENTS "fills", so this is the link between the AC and the map.
		from one_fm.visa_management.doctype.visa_request.visa_request import OCR_DOCUMENTS

		filled = {f for spec in OCR_DOCUMENTS.values() for f in spec["fills"]}

		self.assertEqual(
			filled,
			{"visa_reference_number", "visa_issue_date", "visa_expiry_date", "payment_date"},
		)


class TestTheReapplyScript(FrappeTestCase):
	"""WI-002152: the step the message runs. What it must not do is hold its own opinion
	of what a reapplication is - reapply_visa_request() owns that."""

	SOURCE = "VR-08-2026-00002"
	RAISED = "VR-08-2026-00002-1"

	def run_with(self, already=None):
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request import visa_request as module

		raised = []

		def fake_reapply(name):
			raised.append(name)
			return {"name": self.RAISED}

		with patch.object(module, "existing_reapplication", lambda name: already), patch.object(
			module, "reapply_visa_request", fake_reapply
		):
			result = run_script(REAPPLY_SCRIPT, name=self.SOURCE)

		return result, raised

	def test_it_raises_the_reapplication_and_reports_it(self):
		result, raised = self.run_with()

		self.assertEqual(raised, [self.SOURCE])
		self.assertTrue(result["created"])
		self.assertEqual(result["reapplication"], self.RAISED)
		self.assertEqual(result["reapplied_from"], self.SOURCE)

	def test_a_second_delivery_raises_nothing(self):
		# A double click, or a redelivery. The first arrival already raised it, and a
		# second would be a duplicate visa application - not an error, just nothing to do.
		result, raised = self.run_with(already=self.RAISED)

		self.assertEqual(raised, [])
		self.assertFalse(result["created"])
		self.assertEqual(result["reapplication"], self.RAISED)

	def test_it_reports_the_reapplication_either_way(self):
		# The gateway ahead of it, and the button reading the value back, both need a name
		# whether this delivery raised it or found it.
		for already in (None, self.RAISED):
			with self.subTest(already=already):
				result, _raised = self.run_with(already=already)
				self.assertEqual(result["reapplication"], self.RAISED)


class TestTheReapplyMessageWiring(FrappeTestCase):
	"""The name is the whole correlation, so it is worth a test of its own."""

	def test_the_message_name_is_the_start_event_s_own_name(self):
		# Event_1hlw0sb carries a messageEventDefinition with no messageRef, so
		# SpiffWorkflow takes the message name from the start event's name attribute.
		# REAPPLY_MESSAGE has to be that string exactly or the message is never caught.
		from one_fm.visa_management.doctype.visa_request.visa_request import REAPPLY_MESSAGE

		self.assertEqual(REAPPLY_MESSAGE, "Reapply for Visa")

	def test_the_button_and_the_step_share_one_gate(self):
		# can_reapply() is what the button, request_reapply() and the step all consult.
		# Two gates is how the button starts offering what the server refuses.
		import inspect

		from one_fm.visa_management.doctype.visa_request import visa_request as module

		self.assertIn("can_reapply", inspect.getsource(module.reapply_visa_request))
		self.assertIn("existing_reapplication", inspect.getsource(module.can_reapply))


class TestTheOnceOnlyGate(FrappeTestCase):
	"""WI-002152: delivery is no longer a single click, so raising has to be idempotent."""

	def test_a_request_with_a_reapplication_can_not_be_reapplied_again(self):
		from unittest.mock import patch

		from one_fm.visa_management.doctype.visa_request import visa_request as module

		doc = frappe._dict(
			name="VR-08-2026-00002",
			workflow_state=module.PAM_REJECTED_STATE,
			pam_rejection_remark=module.REAPPLY_REASONS[0],
		)

		with patch.object(module, "existing_reapplication", lambda name: None):
			self.assertTrue(module.can_reapply(doc))

		with patch.object(module, "existing_reapplication", lambda name: "VR-08-2026-00002-1"):
			self.assertFalse(module.can_reapply(doc))

	def test_an_unsaved_request_is_not_matched_against_every_null(self):
		# A {"reapplied_from": None} filter is "IS NULL", which would match every request
		# that was never a reapplication - i.e. almost all of them.
		from one_fm.visa_management.doctype.visa_request.visa_request import (
			existing_reapplication,
		)

		self.assertIsNone(existing_reapplication(None))
		self.assertIsNone(existing_reapplication(""))


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

	def test_the_client_script_no_longer_prompts_for_the_operator_or_pam_reason(self):
		# Both are asked for on the form now and required by the map. The manager and MOI
		# states still prompt here on purpose - see the note in visa_request.js.
		self.assertEqual(
			self.handled_rejection_states(),
			["Pending GRD Manager Approval", "Pending By MOI"],
		)

	def test_the_hardcoded_pam_reason_list_is_gone_from_the_client_script(self):
		# It lives on pam_rejection_remark now. Two lists is how the field starts
		# rejecting a reason the dialog offered.
		self.assertNotIn("REJECTION_REASONS_BY_STATE", self.client_script())

	def test_the_ocr_trigger_is_gone_from_the_controller(self):
		import inspect

		from one_fm.visa_management.doctype.visa_request import visa_request as module

		self.assertFalse(hasattr(module, "queue_document_ocr"))
		self.assertNotIn("ocr", inspect.getsource(module.VisaRequest.on_update).lower())

	def test_the_reading_itself_is_still_in_the_app_for_the_map_to_call(self):
		# The script task calls this by name. Renaming or removing it breaks the step with
		# nothing on the diagram to show why.
		self.assertTrue(
			callable(
				frappe.get_attr(
					"one_fm.visa_management.doctype.visa_request.visa_request.run_document_ocr"
				)
			)
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
