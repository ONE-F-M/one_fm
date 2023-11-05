// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MGRP', {
	onload: function(frm){// Filtering employee field to list only kuwaiti employee as this process only for Kuwaiti's
		frm.set_query("employee", function() {
			return {
				"filters": {
					"one_fm_nationality": "Kuwaiti",
				}
			};
		});
	},employee: function(frm) {
		let {employee} = frm.doc;
		if(employee){
			frappe.db.get_doc("Employee", employee)
			.then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Resignation Form"){
						frm.set_value("end_of_service_attachment", i.attach);
					}
				})
			});
		}
	},
	attach_mgrp_approval: function(frm){
		set_dates(frm);
	},
	status: function(frm) {// Customize naming series upon `status`
		if(status === "Registration"){
			frm.set_value("naming_series", "REG-.{employee}.-");
		}else if(status === "Cancellation"){
			frm.set_value("naming_series", "END-.{employee}.-");
		}
	},
	company_name: function(frm){
		frm.save() // saving the document after selecting the comapny name to fetch the authorized signatory list upon company name
	},
	refresh: function(frm){
		if(frm.doc.company_name){
			//This method is passing company name as argument to (get_signatory_name) method in server side
		   // and it is returning field (arabic names) in child table of pifss Authorized Sinatury doctype 
			frappe.call({
				method: "one_fm.grd.doctype.mgrp.mgrp.get_signatory_name_for_mgrp",
				args:{
					'parent': frm.doc.company_name,
					},
				callback:function(r){
					frm.set_df_property('signatory_name', "options", r.message);
					frm.refresh_field("signatory_name");
					frm.save()
					}
				});
		}
		else{
			frm.set_df_property('signatory_name', "options", null);
			frm.refresh_field("signatory_name");
		}
	},
	signatory_name: function(frm){
		if(frm.doc.signatory_name){
		frappe.call({
			method: "one_fm.grd.doctype.mgrp.mgrp.get_signatory_user_for_mgrp",
			args:{
				'company_name':frm.doc.company_name,
				'user_name':frm.doc.signatory_name,
				},
			callback:function(r){
				frm.set_value('user',r.message[0]);
				frm.set_value('signature',r.message[1]);
				frm.refresh_field("user");
				frm.refresh_field("signature");
				}
			});
	}
	else{
		//frm.set_df_property('user', "options", null);
		frm.set_value('user'," ")
		frm.refresh_field("user");
	}
},
	
});

var set_dates = function(frm){
	frm.set_value('attached_on',frappe.datetime.now_datetime());
}