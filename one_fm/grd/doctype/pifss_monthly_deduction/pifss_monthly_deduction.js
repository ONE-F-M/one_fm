// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('PIFSS Monthly Deduction', {
	attach_report: function(frm) {
		let file_url = frm.doc.attach_report;
		if(file_url){
			frappe.xcall('one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.import_deduction_data', {file_url})
			.then(res => {

				let {deduction_month, table_data} = res;
				frm.set_value("deduction_month", deduction_month);
				if(!res.exc && table_data.length > 0){
					for(let i=0; i < table_data.length; i++){
						let {pifss_id_no, civil_id, total_subscription, employee_deduction} = table_data[i];
						frm.add_child('deductions', {pifss_id_no,civil_id,total_subscription,employee_deduction});
					}
				}
				frm.refresh_field('deduction_month');
				frm.refresh_field('deductions');
			});
		}
	},
	additional_attach_report: function(frm) {
		let file_url = frm.doc.additional_attach_report;
		if(file_url){
			frappe.xcall('one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.import_additional_deduction_data', {file_url})
			.then(res => {
				let {table_data} = res;
				if(!res.exc && table_data.length > 0){
					for(let i=0; i < table_data.length; i++){
						let {pifss_id_no, additional_deduction} = table_data[i];
						if (frm.doc.deductions && additional_deduction){
							$.each(frm.doc.deductions || [], function(i,v){
								if(pifss_id_no == frappe.model.get_value(v.doctype, v.name, "pifss_id_no")){
								frappe.model.set_value(v.doctype, v.name, "additional_deduction", flt(additional_deduction));
								
								}

							})
						}
					}
				}
				frm.refresh_field('deductions');
			});
		}
	},
	remaining_amount: function(frm){
		if(frm.doc.remaining_amount){
			frm.set_value("total_payments",frm.doc.total_sub+frm.doc.remaining_amount+frm.doc.total_additional_deduction);
		}
	}
});

// set total value for additional deduction and employee deduction
frappe.ui.form.on('PIFSS Monthly Deduction', {
    refresh: function(frm){
		if(frm.doc.deductions){
			var total_sub = 0.0;
			var total_deduction = 0.0;
			$.each(frm.doc.deductions || [], function(i, v) {
				let total = frappe.model.get_value(v.doctype, v.name, "additional_deduction") + frappe.model.get_value(v.doctype, v.name, "employee_deduction")
				total = Math.round(total* 1000) / 1000
				frappe.model.set_value(v.doctype, v.name, "total_deductions", total);
			})
			
		}
	}

});
//set the total values for the entire table
frappe.ui.form.on('PIFSS Monthly Deduction', {
    refresh: function(frm){
		if(frm.doc.deductions){
			var total = [0.000,0.000,0.000,0.000]
			$.each(frm.doc.deductions || [], function(i, v) {
				total[0] += frappe.model.get_value(v.doctype, v.name, "total_subscription");
				total[1] += frappe.model.get_value(v.doctype, v.name, "employee_deduction");
				total[2] += frappe.model.get_value(v.doctype, v.name, "additional_deduction");
				total[3] += frappe.model.get_value(v.doctype, v.name, "total_deductions");
			})
		}
		console.log(total[0])
		frm.set_value("total_sub", total[0]);
		frm.set_value("total_deduction", total[1]);
		frm.set_value("total_additional_deduction",total[2]);
		frm.set_value("total_payments",total[2]+frm.doc.remaining_amount+total[0]);
	},

});