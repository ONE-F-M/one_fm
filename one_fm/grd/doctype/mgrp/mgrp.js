// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MGRP', {
	onload: function(frm){
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
	
});

var set_dates = function(frm){
	frm.set_value('attached_on',frappe.datetime.now_datetime());
}