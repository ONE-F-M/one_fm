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

	// MOI -> Pending Visa
	if (action === 'Approve' && frm.doc.workflow_state === 'Pending By MOI') {
		if (frm.doc.moi_reference_number) return;
		return show_reference_validation(frm, 'moi_reference_number', __('MOI Reference Missing'), __('Please add MOI Reference Number before approving to Pending Visa.'));
	}

	// Pending Visa -> Submit to Recruiter: require visa_reference_number, payment_receipt and visa_document
	if (action === 'Submit to Recruiter' && frm.doc.workflow_state === 'Pending Visa') {
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
			'Pending Initial Review',
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

function get_rejection_remarks(frm, resolve, reject) {
	frappe.dom.unfreeze();
	frappe.prompt(
		[
			{
				label: 'Reason for Rejection',
				fieldname: 'reason',
				fieldtype: 'Small Text',
				reqd: 1
			}
		],
		function(values) {
			try {
				const state = frm.doc.workflow_state;
				let target_field = null;

				if (state === 'Pending Initial Review') {
					target_field = 'operator_rejection_remark';
				} else if (state === 'Pending GRD Manager Approval') {
					target_field = 'grd_manager_remark';
				} else if (state === 'Pending By PAM') {
					target_field = 'pam_rejection_remark';
				} else if (state === 'Pending By MOI') {
					target_field = 'moi_rejection_remark';
				}

				if (!target_field) {
					target_field = 'rejection_remarks';
				}

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

