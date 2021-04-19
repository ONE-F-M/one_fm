// // Copyright (c) 2020, omar jaber and contributors
// // For license information, please see license.txt

// frappe.ui.form.on('Work Permit', {
// 	nationality: function(frm) {
// 		frappe.call({
// 			method: 'one_fm.grd.doctype.work_permit.work_permit.get_employee_data_for_work_permit',
// 			args: {'employee_name': frm.doc.employee},
// 			callback: function(r) {
// 				if(r && r.message){
// 					if(frm.doc.nationality == 'Kuwaiti'){
// 						frm.set_value('work_permit_type', 'Renewal Kuwaiti');
// 					}
// 					else{
// 						frm.set_value('work_permit_type', 'Renewal Overseas');
// 					}
// 				}
// 				else{
// 					if(frm.doc.nationality == 'Kuwaiti'){
// 						frm.set_value('work_permit_type', 'New Kuwaiti');
// 					}
// 					else{
// 						frm.set_value('work_permit_type', 'New Overseas');
// 					}
// 				}
// 			}
// 		});
// 	},
// 	work_permit_type: function(frm) {
// 		set_required_documents(frm);
// 	},
// 	employee: function(frm) {
// 		set_required_documents(frm);
// 	},
// 	refresh: function(frm) {
// 		set_grd_supervisor(frm);
// 	},
// 	pam_file: function(frm) {
// 		set_authorized_signatory_name_arabic(frm);
// 	}
// });

// var set_authorized_signatory_name_arabic = function(frm) {
// 	if(frm.doc.pam_file){
// 		frappe.call({
// 			method: 'frappe.client.get',
// 			args: {
// 				doctype: "PAM Authorized Signatory List",
// 				filters: { pam_file_name: frm.doc.pam_file }
// 			},
// 			callback: function(r) {
// 				if(r && r.message && r.message.authorized_signatory && r.message.authorized_signatory.length > 0){
// 					let authorized_signatory = r.message.authorized_signatory[0];
// 					frm.set_value('authorized_signatory_name_arabic', authorized_signatory.authorized_signatory_name_arabic);
// 					frm.set_value('issuer_number', r.message.issuer_number);
// 				}
// 				else{
// 					frm.set_value('authorized_signatory_name_arabic', '');
// 					frm.set_value('issuer_number', '');
// 				}
// 			}
// 		});
// 	}
// 	else{
// 		frm.set_value('authorized_signatory_name_arabic', '');
// 	}
// };

// var set_grd_supervisor = function(frm) {
// 	if(frm.is_new()){
// 		frappe.db.get_value('GRD Settings', {name: 'GRD Settings'}, 'default_grd_supervisor', function(r) {
// 			if(r && r.default_grd_supervisor){
// 				frm.set_value('grd_supervisor', r.default_grd_supervisor);
// 			}
// 		});
// 	}
// };

// var set_required_documents = function(frm) {
// 	frm.clear_table("documents_required");
// 	if(frm.doc.work_permit_type && frm.doc.employee){
// 		frappe.call({
// 			doc: frm.doc,
// 			method: 'get_required_documents',
// 			callback: function(r) {
// 				frm.refresh_field('documents_required');
// 			},
// 			freeze: true,
// 			freeze_message: __('Fetching Data.')
// 		});
//   }
// 	frm.refresh_field('documents_required');
// };
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
                        //frm.set_value('work_permit_type', 'Renewal Overseas');//instead
                        frm.set_value('work_permit_type', 'Renewal Non Kuwaiti');//Renewal Non Kuwaiti 
                    }
                }
                else{
                    if(frm.doc.nationality == 'Kuwaiti'){
                        frm.set_value('work_permit_type', 'New Kuwaiti');
                    }
                    else{
                        //frm.set_value('work_permit_type', 'New Overseas');
                        frm.set_value('work_permit_type', 'New Non Kuwaiti');//Add new option for (New Non Kuwaiti)
                    }   
                }
            }
        });
    },//the work permit type will be set automatically based on employee nationality
    work_permit_type: function(frm) {
        set_required_documents(frm);
    },
    employee: function(frm) {
        set_required_documents(frm);
    },
    refresh: function(frm) {
        set_grd_supervisor(frm);
    },
    pam_file: function(frm) {
        set_authorized_signatory_name_arabic(frm);
    }
});

var set_authorized_signatory_name_arabic = function(frm) {
    if(frm.doc.pam_file){
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: "PAM Authorized Signatory List",
                filters: { pam_file_name: frm.doc.pam_file }
            },
            callback: function(r) {
                if(r && r.message && r.message.authorized_signatory && r.message.authorized_signatory.length > 0){
                    let authorized_signatory = r.message.authorized_signatory[0];
                    frm.set_value('authorized_signatory_name_arabic', authorized_signatory.authorized_signatory_name_arabic);
                    frm.set_value('issuer_number', r.message.issuer_number);
                }
                else{
                    frm.set_value('authorized_signatory_name_arabic', '');
                    frm.set_value('issuer_number', '');
                }
            }
        });
    }
    else{
        frm.set_value('authorized_signatory_name_arabic', '');
    }
};

var set_grd_supervisor = function(frm) {
    if(frm.is_new()){
        frappe.db.get_value('GRD Settings', {name: 'GRD Settings'}, 'default_grd_supervisor', function(r) {
            if(r && r.default_grd_supervisor){
                frm.set_value('grd_supervisor', r.default_grd_supervisor);//the field in the work permit will be set based on the default_grd_supervisor field in GRD settings
            }
        });
    }
};

var set_required_documents = function(frm) {
    frm.clear_table("documents_required");
    if(frm.doc.work_permit_type && frm.doc.employee){
        frappe.call({
            doc: frm.doc,
            method: 'get_required_documents',
            callback: function(r) {
                frm.refresh_field('documents_required');
            },
            freeze: true,
            freeze_message: __('Fetching Data.')
        });
  }
    frm.refresh_field('documents_required');
};
