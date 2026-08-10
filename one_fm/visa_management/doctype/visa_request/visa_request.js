// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Visa Request", {
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
// which field reasons_for_state() reads its options off.
const REJECTION_REMARK_FIELD_BY_STATE = {
	'Pending by GRD Operator': 'operator_rejection_remark',
	'Pending GRD Manager Approval': 'grd_manager_remark',
	'Pending By PAM': 'pam_rejection_remark',
	'Pending By MOI': 'moi_rejection_remark'
};

// Predefined rejection reasons per workflow state (WI-001693). PAM and MOI reject for
// different reasons, so each state offers its own list rather than a shared one.
// MOI is absent on purpose: WI-001773 made moi_rejection_remark a Select, so its
// reasons come from the field itself via reasons_for_state() rather than being
// repeated here, where they would only drift from what the field accepts.
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
// value the field rejects on save.
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
	// PAM & MOI require a predefined reason (Select), each from its own list; the other
	// states keep free text.
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
