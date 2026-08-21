// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// WI-001976: the state and the two PAM reasons a fresh attempt is worth making under.
// Kept in step with REAPPLY_REASONS in visa_request.py - the server refuses anything else,
// so a button offered outside these would only produce an error dialog.
const PAM_REJECTED_STATE = 'Rejected By PAM';
const REAPPLY_REASONS = [
	"The occupation requires amendment to specify the worker's specialization",
	"The worker's gender does not match the profession"
];

frappe.ui.form.on("Visa Request", {
	refresh: function(frm) {
		add_reapply_button(frm);
	},

	before_workflow_action: async function(frm) {
		try {
			let action = frm.selected_workflow_action;
			// run the modular checks; each helper returns a Promise to block the workflow when necessary
			let result;

			// consolidated check for required references/documents per workflow transition
			result = validate_references(frm, action);
			if (result) return result;

			// Reject handling
			if (action === 'Reject') {
				return set_rejection_remarks(frm);
			}
		} catch (e) {
			console.error('Error in before_workflow_action (visa_request):', e);
		}
	}
});

// WI-002106: the MOI Reference Number check (AC 5) and the visa reference / payment
// receipt / visa document check (AC 7) were removed from here. Both are now enforced by
// the Processa map, which blocks the task rather than the button.
//
// The PAM Reference Number check stays until the process owner settles which stage it
// belongs to - see the note in validate_workflow_transitions().
function validate_references(frm, action) {
	// PAM -> MOI
	if (action === 'Approve' && frm.doc.workflow_state === 'Pending By PAM') {
		if (frm.doc.pam_reference_number) return;
		return show_reference_validation(frm, 'pam_reference_number', __('PAM Reference Missing'), __('Please add PAM Reference Number before approving to MOI.'));
	}
}

function show_reference_validation(frm, field, title, message) {
	return new Promise((resolve, reject) => {
		try {
			frappe.dom.unfreeze();
			// field may be a string or an array; if array, scroll to first
			if (Array.isArray(field) && field.length) {
				frm.scroll_to_field(field[0]);
			} else if (typeof field === 'string' && field) {
				frm.scroll_to_field(field);
			}

			frappe.msgprint({
				title: title,
				message: message,
				indicator: 'red'
			});
		} catch (e) {
			console.error('Error in block_and_reject:', e);
		}
		reject();
	});
}

function set_rejection_remarks(frm) {
	try {
		const state = frm.doc.workflow_state;
		// WI-002106: the GRD Operator rejection reason is now required by the Processa
		// map - Activity_0sa0xb3, Server Script "Require Rejection Reason" - which
		// blocks the task instead of prompting in a dialog.
		//
		// The other three states still prompt here:
		//
		//   Pending GRD Manager Approval  no script yet (Activity_0nxcbzb)
		//   Pending By MOI                no script yet (Activity_0dtjaug), AC 6
		//   Pending By PAM                AC 3 wants the reason on a dropdown with the
		//                                 remarks kept separately, and that field does
		//                                 not exist yet
		//
		// The manager and MOI shapes are not merely unscripted, they are mis-bound: both
		// carry the inline text "Require Rejection Reason", and the compiler reads that
		// text as a Server Script name when no serverScript attribute is set. So they
		// currently resolve to the OPERATOR script and would demand
		// operator_rejection_remark on a manager or MOI rejection. Removing these two
		// branches before each shape has its own name and an explicit attribute would
		// swap a working dialog for a check on the wrong field.
		const handledStates = [
			'Pending GRD Manager Approval',
			'Pending By PAM',
			'Pending By MOI'
		];

		if (handledStates.includes(state)) {
			return new Promise((resolve, reject) => {
				get_rejection_remarks(frm, resolve, reject);
			});
		}
	} catch (e) {
		console.error('Error handling Reject before_workflow_action:', e);
	}
}

// Where a rejection reason is stored, per the state it was rejected from. Also decides
// which field reasons_for_state() reads its options off.
const REJECTION_REMARK_FIELD_BY_STATE = {
	// The operator entry went with its state in WI-002106 - unreachable once the dialog
	// stopped handling it, and the reason is now written on the form instead.
	'Pending GRD Manager Approval': 'grd_manager_remark',
	'Pending By PAM': 'pam_rejection_remark',
	'Pending By MOI': 'moi_rejection_remark'
};

// Predefined rejection reasons per workflow state (WI-001693). Only PAM has a hardcoded
// list; MOI reads its options off moi_rejection_remark via reasons_for_state(), and the
// manager state keeps free text.
//
// AC 3 will move this list onto the field itself as a Select, the way
// moi_rejection_remark already was - which is what reasons_for_state() below prefers,
// and what stops the options here drifting from what the field accepts. That needs the
// process owner to confirm the field split and the authoritative list first.
const REJECTION_REASONS_BY_STATE = {
	'Pending By PAM': [
		'Passport Validity is Less than 18 Months',
		"Worker's age is below the legal minimum",
		"The worker's gender does not match the profession",
		"The occupation requires amendment to specify the worker's specialization",
		'An active file exists for this worker',
		'Worker is in Black List'
	]
};

// The reasons to offer for a state: the target field's own options when it is a
// Select, otherwise the hardcoded list above. Offering anything else would write a
// value the field rejects on save. Kept field-driven-first precisely because AC 3 is
// going to turn pam_rejection_remark into a Select.
function reasons_for_state(frm, state) {
	const fieldname = REJECTION_REMARK_FIELD_BY_STATE[state];
	const df = fieldname && frappe.meta.get_docfield('Visa Request', fieldname, frm.doc.name);

	if (df && df.fieldtype === 'Select') {
		const options = (df.options || '').split('\n').filter(o => o);
		if (options.length) return options;
	}

	return REJECTION_REASONS_BY_STATE[state];
}

function get_rejection_remarks(frm, resolve, reject) {
	frappe.dom.unfreeze();
	// PAM is the only state that still reaches here, and it offers a predefined list.
	const state_reasons = reasons_for_state(frm, frm.doc.workflow_state);
	const reason_field = state_reasons
		? {
			label: 'Reason for Rejection',
			fieldname: 'reason',
			fieldtype: 'Select',
			options: state_reasons.join('\n'),
			reqd: 1
		}
		: {
			label: 'Reason for Rejection',
			fieldname: 'reason',
			fieldtype: 'Small Text',
			reqd: 1
		};
	frappe.prompt(
		[reason_field],
		function(values) {
			try {
				const state = frm.doc.workflow_state;
				const target_field = REJECTION_REMARK_FIELD_BY_STATE[state] || 'rejection_remarks';

				frappe.dom.freeze();
				frm.set_value(target_field, values.reason);
				try {
					if (frm.fields_dict && frm.fields_dict[target_field]) {
						frm.refresh_field(target_field);
					}
				} catch (e) {
					// ignore refresh errors
				}

				frm.save()
					.then(() => resolve())
					.catch(err => reject(err));
			} catch (err) {
				frappe.dom.unfreeze();
				reject(err);
			}
		},
		'Enter Rejection Remark',
		'Proceed'
	);
}


// WI-001976: PAM rejections for the designation or the worker's gender are worth another
// attempt with the application corrected - a black-listed worker or an active file would
// be refused again for the same cause, so the button is not offered there.
function add_reapply_button(frm) {
	if (frm.is_new()) return;
	if (frm.doc.workflow_state !== PAM_REJECTED_STATE) return;
	if (!REAPPLY_REASONS.includes(frm.doc.pam_rejection_remark)) return;

	frm.add_custom_button(__('Reapply Visa'), () => {
		frappe.confirm(
			__('Raise a new Visa Request from {0}? The rejected one is kept as history.', [frm.doc.name]),
			() => {
				frappe.call({
					method: 'one_fm.visa_management.doctype.visa_request.visa_request.reapply_visa_request',
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __('Reapplying...'),
					callback: (r) => {
						if (!r.message) return;
						frappe.show_alert({ message: __('Created {0}', [r.message.name]), indicator: 'green' });
						frappe.set_route('Form', 'Visa Request', r.message.name);
					}
				});
			}
		);
	});
}


// WI-001977: OCR runs in the background after a Visa Copy or Payment Receipt is
// attached, so the extracted values arrive after the save has already returned. Without
// this the operator would be looking at a stale form and would key them in by hand.
frappe.ui.form.on("Visa Request", {
	onload: function(frm) {
		if (frm.__ocr_listener) return;
		frm.__ocr_listener = true;

		frappe.realtime.on("visa_request_ocr_complete", (data) => {
			if (!data || data.name !== frm.doc.name) return;

			frm.reload_doc().then(() => {
				frappe.show_alert({
					message: __("Read from the attachment: {0}. Please check the values.", [
						(data.fields || []).map((f) => frappe.meta.get_label("Visa Request", f)).join(", ")
					]),
					indicator: "green"
				}, 10);
			});
		});
	}
});
