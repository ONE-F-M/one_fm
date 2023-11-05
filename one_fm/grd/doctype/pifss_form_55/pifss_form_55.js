// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('PIFSS Form 55', {
	attach_report: function(frm) {
		let file_url = frm.doc.attach_report;
		console.log(file_url);
		if(file_url){
			frappe.xcall('one_fm.grd.doctype.pifss_form_55.pifss_form_55.import_deduction_data', {file_url})
			.then(res => {
				console.log(res);
				if(!res.exc && res.length > 0){
					for(let i=0; i < res.length; i++){
						let {civil_id, full_name_arabic, social_allowance, qualification_bonus, financial_reward} = res[i];
						frm.add_child('employees', {civil_id, full_name_arabic, social_allowance, qualification_bonus, financial_reward});
					}
				}
				frm.refresh_field('employees');
			});
		}
	}
});
