// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// WI-001976: the state and the two PAM reasons a fresh attempt is worth making under.
// Kept in step with REAPPLY_REASONS in visa_request.py - the server refuses anything else,
// so a button offered outside these would only produce an error dialog.
const PAM_REJECTED_STATE = 'Rejected By PAM';

// WI-002313: the state a completed visa can be cancelled from.
const COMPLETED_STATE = 'Completed';
const REAPPLY_REASONS = [
	"The occupation requires amendment to specify the worker's specialization",
	"The worker's gender does not match the profession"
];

frappe.ui.form.on("Visa Request", {
	refresh: function(frm) {
		add_reapply_button(frm);
		add_visa_cancellation_button(frm);
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

function validate_references(frm, action) {
	// PAM -> MOI
	if (action === 'Approve' && frm.doc.workflow_state === 'Pending By PAM') {
		if (frm.doc.pam_reference_number) return;
		return show_reference_validation(frm, 'pam_reference_number', __('PAM Reference Missing'), __('Please add PAM Reference Number before approving to MOI.'));
	}

	// MOI -> Pending Visa Issuance
	if (action === 'Approve' && frm.doc.workflow_state === 'Pending By MOI') {
		if (frm.doc.moi_reference_number) return;
		return show_reference_validation(frm, 'moi_reference_number', __('MOI Reference Missing'), __('Please add MOI Reference Number before approving to Pending Visa Issuance.'));
	}

	// Pending Visa Issuance -> Submit to Recruiter: require visa_reference_number, payment_receipt and visa_document
	if (action === 'Submit to Recruiter' && frm.doc.workflow_state === 'Pending Visa Issuance') {
		const missing = [];
		if (!frm.doc.visa_reference_number) missing.push({field: 'visa_reference_number', label: __('Visa Reference Number')});
		if (!frm.doc.payment_receipt) missing.push({field: 'payment_receipt', label: __('Payment Receipt')});
		if (!frm.doc.visa_document) missing.push({field: 'visa_document', label: __('Visa Document')});
		if (missing.length) {
			return show_reference_validation(frm, missing[0].field, __('Missing Required Fields'), __('Please add {0} before submitting to recruiter.', [missing.map(m => m.label).join(', ')]));
		}
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
		const handledStates = [
			'Pending by GRD Operator',
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
// which field the prompt reads its options off.
const REJECTION_REMARK_FIELD_BY_STATE = {
	'Pending by GRD Operator': 'operator_rejection_remark',
	'Pending GRD Manager Approval': 'grd_manager_remark',
	'Pending By PAM': 'pam_rejection_remark',
	'Pending By MOI': 'moi_rejection_remark'
};

// WI-001773 made moi_rejection_remark a Select, so the reasons on offer have to come
// from the field itself - a free-text remark would fail _validate_selects on save.
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
	const state_reasons = reasons_for_state(frm, frm.doc.workflow_state);
	const reason_field = state_reasons
		? {
			label: 'Reason for Rejection',
			fieldname: 'reason',
			fieldtype: 'Select',
			options: state_reasons,
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


// WI-002313: a completed visa is the one a recruiter asks to cancel - the workflow's own
// "Request to Cancel" is offered at Pending Recruiter Confirmation, which is the state
// before the visa exists to cancel.
//
// ponytail: the button is a placeholder. The Visa Cancellation DocType it will raise does
// not exist yet - the business analyst is creating it - and the Completed state is
// submitted (docstatus 1) while every cancellation state in the workflow is a draft, so
// there is no legal transition to send it down either. Replace the handler with the
// document creation once the DocType lands; the visibility rule above is the AC and stays.
function add_visa_cancellation_button(frm) {
	if (frm.is_new()) return;
	if (frm.doc.workflow_state !== COMPLETED_STATE) return;

	frm.add_custom_button(__('Create Visa Cancellation'), () => ask_for_cancellation_reason(frm));
}

// WI-002428: the reason has to be chosen before the cancellation process starts, so it is
// asked for here rather than left to be filled in on the document afterwards.
//
// The options are read off the DocType's own Select rather than repeated here, so the
// dialog cannot drift from the field the answer is stored in. reqd on the dialog field is
// what stops an empty submission; the server demands it again, because the dialog is a
// convenience and not the rule.
function ask_for_cancellation_reason(frm) {
	// The meta has to be loaded before it can be read, and this is the one place in this
	// app that reads a DocType the open form has nothing to do with. frappe.meta reads
	// locals.DocType, which a browser only fills in for doctypes it has actually loaded -
	// so in a session that had never opened a Visa Cancellation Request the dropdown came
	// up empty, and started working later only because visiting the DocType once had
	// cached its meta. with_doctype fetches it when it is missing and calls straight back
	// when it is not.
	frappe.model.with_doctype('Visa Cancellation Request', () => {
		open_cancellation_reason_dialog(frm);
	});
}

function open_cancellation_reason_dialog(frm) {
	const reasons = (frappe.meta.get_docfield('Visa Cancellation Request', 'cancellation_reason')
		|| {}).options || '';

	// An empty Select is a dead end the user cannot act on and cannot explain. Say so
	// rather than opening a dialog whose only control is blank.
	if (!reasons.trim()) {
		frappe.msgprint({
			title: __('No Cancellation Reasons Configured'),
			message: __('The Cancellation Reason field on Visa Cancellation Request offers no options. Run bench migrate, or add the reasons to the field.'),
			indicator: 'red'
		});
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: __('Reason for Visa Cancellation'),
		fields: [
			{
				fieldname: 'cancellation_reason',
				fieldtype: 'Select',
				label: __('Cancellation Reason'),
				options: reasons,
				reqd: 1
			}
		],
		primary_action_label: __('Create Visa Cancellation'),
		primary_action(values) {
			dialog.hide();
			frappe.call({
				method: 'one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request.create_from_visa_request',
				args: {
					visa_request: frm.doc.name,
					cancellation_reason: values.cancellation_reason
				},
				freeze: true,
				freeze_message: __('Raising the Visa Cancellation Request...'),
				callback: (r) => {
					if (r.message && r.message.name) {
						frappe.set_route('Form', 'Visa Cancellation Request', r.message.name);
					}
				}
			});
		}
	});

	dialog.show();
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
