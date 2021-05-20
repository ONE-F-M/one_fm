// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('PIFSS Monthly Deduction', {
	attach_report: function(frm) {
		let file_url = frm.doc.attach_report;
		// console.log(file_url);
		if(file_url){
			frappe.xcall('one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.import_deduction_data', {file_url})
			.then(res => {
				console.log(res);
				let {deduction_month, table_data} = res;
				frm.set_value("deduction_month", deduction_month);
				if(!res.exc && table_data.length > 0){
					for(let i=0; i < table_data.length; i++){
						let {pifss_id_no, total_subscription} = table_data[i];
						frm.add_child('deductions', {pifss_id_no, total_subscription});
					}
				}
				frm.refresh_field('deduction_month');
				frm.refresh_field('deductions');
			});
		}
	}
});
