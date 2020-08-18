// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Permit', {
	nationality: function(frm) {
		frappe.call({
			method: 'one_fm.grd.doctype.work_permit.work_permit.get_employee_data_for_work_permit',
			args: {'employee_name': frm.doc.employee},
			callback: function(r) {
				if(r && r.message){
					if(frm.doc.nationality == 'Kuwaiti'){
						frm.set_value('work_permit_type', 'Renewal Kuwaiti');
					}
					else{
						frm.set_value('work_permit_type', 'Renewal Overseas');
					}
				}
				else{
					if(frm.doc.nationality == 'Kuwaiti'){
						frm.set_value('work_permit_type', 'New Kuwaiti');
					}
					else{
						frm.set_value('work_permit_type', 'New Overseas');
					}
				}
			}
		});
	},
	work_permit_type: function(frm) {
		set_required_documents(frm);
	}
});

var set_required_documents = function(frm) {
	frm.clear_table("documents_required");
	if(frm.doc.work_permit_type){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: "Work Permit Required Documents Template",
				filters: {'work_permit_type':frm.doc.work_permit_type}
			},
			callback: function(r) {
				if(r.message && r.message.work_permit_document){
					var doc_list = r.message.work_permit_document;
					doc_list.forEach((item, i) => {
						let child_item = frappe.model.add_child(frm.doc, 'Work Permit Required Documents', 'documents_required');
						frappe.model.set_value(child_item.doctype, child_item.name, 'required_document', item.required_document);
					});
				}
				frm.refresh_field('documents_required');
			},
			freeze: true,
			freeze_message: __('Fetching Data.')
		});
  }
	frm.refresh_field('documents_required');
};
