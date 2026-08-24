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
		// WI-002106: the GRD Operator rejection reason (Activity_0sa0xb3) and the PAM one
		// (Activity_1pgghs6, AC 3) are now required by the Processa map, which blocks the
		// task instead of prompting in a dialog. Both reasons are typed on the form -
		// pam_rejection_remark is the dropdown AC 3 asks for, with pam_rejection_remarks
		// alongside it for the free text.
		//
		// The manager and MOI states still prompt here. Each has its own script on the
		// map now, so both branches can follow the same way - but that is the next
		// change, not this one: whoever makes it should check the shape carries an
		// explicit serverScript attribute first, and that the field it reads is not
		// read-only (see the operator field in the doctype JSON, which this work item
		// had to make writable for exactly that reason).
		const handledStates = [
			'Pending GRD Manager Approval',
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
	// The operator and PAM entries went with their states in WI-002106 - unreachable once
	// the dialog stopped handling them, and both reasons are written on the form instead.
	'Pending GRD Manager Approval': 'grd_manager_remark',
	'Pending By MOI': 'moi_rejection_remark'
};

// The reasons to offer for a state: the target field's own options. WI-002106 removed the
// hardcoded PAM list from here - AC 3 put it on pam_rejection_remark as a Select, the way
// moi_rejection_remark already was, so the field is the one source of truth for what is
// offered and the two cannot drift. Undefined for a free-text field, which is what the
// manager state wants.
function reasons_for_state(frm, state) {
	const fieldname = REJECTION_REMARK_FIELD_BY_STATE[state];
	const df = fieldname && frappe.meta.get_docfield('Visa Request', fieldname, frm.doc.name);

	if (df && df.fieldtype === 'Select') {
		const options = (df.options || '').split('\n').filter(o => o);
		if (options.length) return options;
	}
}

function get_rejection_remarks(frm, resolve, reject) {
	frappe.dom.unfreeze();
	// MOI offers its own Select options; the manager state takes free text.
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


// WI-001977: the extracted values are written straight to the database, so the form the
// operator is looking at does not have them. WI-002106 moved the reading into the map -
// it now happens during the Reject/Submit action rather than on a save - but the push is
// still what tells the operator which fields were read and that they are worth checking.
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
