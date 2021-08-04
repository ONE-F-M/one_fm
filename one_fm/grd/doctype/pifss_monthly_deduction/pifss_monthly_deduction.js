// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('PIFSS Monthly Deduction', {
	
	fetch_data: function(frm) {
		console.log(frm.doc.fetch_data)
		let file_url = frm.doc.attach_report;
		if(file_url){
			frappe.xcall('one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.import_deduction_data', {file_url})
			.then(res => {

				let {deduction_month, table_data} = res;
				frm.set_value("deduction_month", deduction_month);
				if(!res.exc && table_data.length > 0){
					for(let i=0; i < table_data.length; i++){
						let {pifss_id_no, civil_id, total_subscription, compensation_amount,unemployment_insurance,fund_increase,supplementary_insurance,basic_insurance,employee_deduction} = table_data[i];
						frm.add_child('deductions', {pifss_id_no,civil_id,total_subscription,compensation_amount,unemployment_insurance,fund_increase,supplementary_insurance,basic_insurance,employee_deduction});
					}
				}
				frm.refresh_field('deduction_month');
				frm.refresh_field('deductions');
				set_value_of_csv_file(frm);
			});
			
		};	
		
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
	refresh:function(frm){
		document.querySelectorAll("[data-fieldname='fetch_data']")[1].style.backgroundColor ="#44c95a";
		if(!frm.doc.basic_insurance){
			frm.set_value("difference_in_basic_insurance", 0);
		}if(!frm.doc.supplementary_insurance){
			frm.set_value("difference_supplementary_insurance", 0);
		}if(!frm.doc.fund_increase){
			frm.set_value("difference_fund_increase", 0);
		}if(!frm.doc.unemployment_insurance){
			frm.set_value("difference_unemployment_insurance", 0);
		}if(!frm.doc.compensation){
			frm.set_value("difference_compensation", 0);
		}
		
	},
	remaining_amount: function(frm){
		if(frm.doc.remaining_amount){
			frm.set_value("total_payments",frm.doc.total_sub+frm.doc.remaining_amount+frm.doc.total_additional_deduction);
		}
	},
	basic_insurance: function(frm){
		if(frm.doc.basic_insurance){
			frm.set_value("difference_in_basic_insurance", frm.doc.basic_insurance-frm.doc.basic_insurance_in_csv);
		}if(frm.doc.difference_in_basic_insurance!=0 ){
			document.querySelectorAll("[data-fieldname='difference_in_basic_insurance']")[1].style.backgroundColor ="red";
		}
	},
	supplementary_insurance: function(frm){
		if(frm.doc.supplementary_insurance){
			frm.set_value("difference_supplementary_insurance",frm.doc.supplementary_insurance-frm.doc.supplementary_insurance_in_csv);
		}if (frm.doc.difference_supplementary_insurance!=0){
			document.querySelectorAll("[data-fieldname='difference_supplementary_insurance']")[1].style.backgroundColor ="red";
			
		}
	},
	fund_increase: function(frm){
		if(frm.doc.fund_increase){
			frm.set_value("difference_fund_increase",frm.doc.fund_increase-frm.doc.fund_increase_in_csv);
		}if (frm.doc.difference_supplementary_insurance!=0){
			document.querySelectorAll("[data-fieldname='difference_fund_increase']")[1].style.backgroundColor ="red";
		}
	},
	unemployment_insurance: function(frm){
		if(frm.doc.unemployment_insurance){
			frm.set_value("difference_unemployment_insurance",frm.doc.unemployment_insurance-frm.doc.unemployment_insurance_in_csv);
		}if (frm.doc.difference_unemployment_insurance!=0){
			$('input[data-fieldname="difference_unemployment_insurance"]').css("color","red")
			// $('input[data-fieldname="difference_unemployment_insurance"]').css("background-color","#FFE4C4")
			document.querySelectorAll("[data-fieldname='difference_unemployment_insurance']")[1].style.backgroundColor ="red";
		}
	},
	compensation: function(frm){
		if(frm.doc.unemployment_insurance){
			frm.set_value("difference_compensation",frm.doc.compensation-frm.doc.compensation_in_csv);
		}if (frm.doc.difference_compensation!=0){
			// $('input[data-fieldname="difference_compensation"]').css("background-color","#FFE4C4")
			document.querySelectorAll("[data-fieldname='difference_compensation']")[1].style.backgroundColor ="red";
		}
	},
	// open_collapse_sections: function(frm){
	// 	check_collapse_sections(frm);
	// }
		
});
// var check_collapse_sections =function(frm){
// 	if(frm.doc.workflow_state != "Pending By Finance" && frm.doc.open_collapse_sections == 0){
// 		frm.fields_dict['finance_section_section'].collapse(0);
// 	}if(frm.doc.workflow_state != "Pending By Finance" && frm.doc.open_collapse_sections != 0){
// 		frm.fields_dict['finance_section_section'].collapse(1);
// 	}if(frm.doc.workflow_state == "Pending By Finance" && frm.doc.open_collapse_sections == 0){
// 		frm.fields_dict['section_break_4'].collapse(0);
// 		frm.fields_dict['section_break_8'].collapse(0);
// 		frm.fields_dict['detailed_basic_amounts_section'].collapse(0);
// 		frm.fields_dict['detailed_additional_amounts_section'].collapse(0);
// 	}if(frm.doc.workflow_state == "Pending By Finance" && frm.doc.open_collapse_sections != 0){
// 		frm.fields_dict['section_break_4'].collapse(1);
// 		frm.fields_dict['section_break_8'].collapse(1);
// 		frm.fields_dict['detailed_basic_amounts_section'].collapse(1);
// 		frm.fields_dict['detailed_additional_amounts_section'].collapse(1);
// 	}
// };
var set_value_of_csv_file = function(frm){
	if(frm.doc.deductions){
		var total = [0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000]
		$.each(frm.doc.deductions || [], function(i, v) {
			total[0] += frappe.model.get_value(v.doctype, v.name, "total_subscription");
			total[1] += frappe.model.get_value(v.doctype, v.name, "employee_deduction");
			total[2] += frappe.model.get_value(v.doctype, v.name, "additional_deduction");
			total[3] += frappe.model.get_value(v.doctype, v.name, "total_deductions");
			total[4] += frappe.model.get_value(v.doctype, v.name, "basic_insurance");
			total[5] += frappe.model.get_value(v.doctype, v.name, "supplementary_insurance");
			total[6] += frappe.model.get_value(v.doctype, v.name, "fund_increase");
			total[7] += frappe.model.get_value(v.doctype, v.name, "unemployment_insurance");
			total[8] += frappe.model.get_value(v.doctype, v.name, "compensation_amount");

		})
		
	}
	
	frm.set_value("total_sub", total[0]);
	frm.set_value("total_deduction", total[1]);
	frm.set_value("total_additional_deduction",total[2]);
	frm.set_value("total_payments",total[2]+frm.doc.remaining_amount+total[0]);
	frm.set_value("basic_insurance_in_csv", total[4]);
	frm.set_value("supplementary_insurance_in_csv", total[5]);
	frm.set_value("fund_increase_in_csv", total[6]);
	frm.set_value("unemployment_insurance_in_csv", total[7]);
	frm.set_value("compensation_in_csv", total[8]);


};
// set total value for additional deduction and employee deduction
frappe.ui.form.on('PIFSS Monthly Deduction', {
    onload: function(frm){
		if(frm.doc.deductions){
			// var total_sub = 0.0;
			// var total_deduction = 0.0;
			$.each(frm.doc.deductions || [], function(i, v) {
				let total = frappe.model.get_value(v.doctype, v.name, "additional_deduction") + frappe.model.get_value(v.doctype, v.name, "employee_deduction")
				total = Math.round(total* 1000) / 1000
				frappe.model.set_value(v.doctype, v.name, "total_deductions", total);
			})
			
		};
		
		
		
	}
	

});
