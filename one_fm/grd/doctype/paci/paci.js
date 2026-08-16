// Copyright (c) 2021, ONE FM and contributors
// For license information, please see license.txt
frappe.ui.form.on('PACI', {
	// onload: function(frm){
        // set_employee_details(frm);
    // },
    employee: function(frm){
        set_employee_details(frm);
    },
	upload_civil_id_payment: function(frm){
		set_upload_civil_id_payment(frm);
        set_status(frm);
	},
	upload_civil_id: function(frm){
		set_upload_civil_id(frm);
	},

});
var set_employee_details = function(frm){
    if(frm.doc.employee){
        frappe.call({
            method:"frappe.client.get_value",//api calls
            args: {
                doctype:"Employee",
                filters: {
                name: frm.doc.employee
                },
                fieldname:["one_fm_first_name_in_arabic","one_fm_second_name_in_arabic","one_fm_third_name_in_arabic","one_fm_last_name_in_arabic",
				"first_name","middle_name","one_fm_third_name","last_name","one_fm_civil_id", "work_permit_expiry_date",
				"passport_number","one_fm_pam_designation","one_fm_nationality","employee_id","residency_expiry_date"]
            }, 
            callback: function(r) { 
                // set the returned value in a field
                frm.set_value('first_name_arabic', r.message.one_fm_first_name_in_arabic);
                frm.set_value('second_name_arabic', r.message.one_fm_second_name_in_arabic);
                frm.set_value('third_name_arabic', r.message.one_fm_third_name_in_arabic);
                frm.set_value('last_name_arabic', r.message.one_fm_last_name_in_arabic);
                frm.set_value('first_name_english',r.message.first_name);
                frm.set_value('second_name_english', r.message.middle_name);
                frm.set_value('third_name_english', r.message.one_fm_third_name);
                frm.set_value('last_name_english',r.message.last_name);
                frm.set_value('civil_id', r.message.one_fm_civil_id);
                frm.set_value('passport_number', r.message.passport_number);
                frm.set_value('pam_designation', r.message.one_fm_pam_designation);
                frm.set_value('nationality', r.message.one_fm_nationality);
				frm.set_value('employee_id', r.message.employee_id);
                frm.set_value('residency_expiry_date',r.message.residency_expiry_date);
               
            }
        })
    }
};
var set_upload_civil_id_payment = function(frm)
{//2
	if((frm.doc.upload_civil_id_payment) && (!frm.doc.upload_civil_id_payment_datetime))
	{ 
		frm.set_value('upload_civil_id_payment_datetime',frappe.datetime.now_datetime());
	}if((!frm.doc.upload_civil_id_payment) && (frm.doc.upload_civil_id_payment_datetime))
	{
		frm.set_value('upload_civil_id_payment_datetime',null);
	}
};
var set_upload_civil_id = function(frm)
{//3
	if((frm.doc.upload_civil_id) && (!frm.doc.upload_civil_id_datetime))
	{
		frm.set_value('upload_civil_id_datetime',frappe.datetime.now_datetime());
	}if((!frm.doc.upload_civil_id) && (frm.doc.upload_civil_id_datetime))
	{
		frm.set_value('upload_civil_id_datetime',null);
	}
};
var set_status = function(frm)
{
    if (frm.doc.upload_civil_id_payment){
        frm.set_value('paci_status',"Under-Process");
    }
};
// WI-001830 AC3/AC4: a rejection has to say why, and a rejected application can be
// raised again without re-entering the candidate. The states either side of this are
// PACI's own - Pending by PACI rejects to Rejected, and Rejected is where Reapply lives.
const PACI_REJECTING_STATE = 'Pending by PACI';
const PACI_REJECTED_STATE = 'Rejected';

frappe.ui.form.on('PACI', {
	refresh: function(frm) {
		add_reapply_button(frm);
	},

	before_workflow_action: function(frm) {
		if (frm.selected_workflow_action !== 'Reject') return;
		if (frm.doc.workflow_state !== PACI_REJECTING_STATE) return;

		return ask_for_paci_rejection_reason(frm);
	}
});

function ask_for_paci_rejection_reason(frm) {
	// Options come from the field itself rather than a list kept here, which would only
	// drift from what the field will accept on save.
	const df = frappe.meta.get_docfield('PACI', 'paci_rejection_reason', frm.doc.name);
	const options = (df && df.options ? df.options : '').split('\n').filter(o => o);

	return new Promise((resolve, reject) => {
		frappe.prompt(
			[{
				label: __('PACI Rejection Reason'),
				fieldname: 'reason',
				fieldtype: 'Select',
				options: options.join('\n'),
				reqd: 1
			}],
			(values) => {
				frm.set_value('paci_rejection_reason', values.reason);
				frm.save().then(resolve).catch(reject);
			},
			__('PACI Rejection Reason'),
			__('Reject')
		);

		// Frappe freezes the form for a workflow action; the prompt is unusable until it
		// is released.
		frappe.dom.unfreeze();
	});
}

function add_reapply_button(frm) {
	if (frm.is_new() || frm.doc.workflow_state !== PACI_REJECTED_STATE) return;

	frm.add_custom_button(__('Reapply'), () => {
		frappe.confirm(
			__('Raise a new PACI from {0}? The rejected one is kept as history.', [frm.doc.name]),
			() => {
				frappe.call({
					method: 'one_fm.grd.doctype.paci.paci.reapply_paci',
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __('Reapplying...'),
					callback: (r) => {
						if (!r.message) return;
						frappe.show_alert({ message: __('Created {0}', [r.message.name]), indicator: 'green' });
						frappe.set_route('Form', 'PACI', r.message.name);
					}
				});
			}
		);
	});
}
