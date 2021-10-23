// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt
frappe.ui.form.on('PIFSS Monthly Deduction', {

	fetch_data: function(frm) {
		/*
		This is an Ajax call that calls a method with a document name as an argument,
		the callback is a dictionary list of the 2 attached files(csv file and additional report file),
		then, it will add the dictionary into the deductions table.
		*/
		if(frm.doc.__unsaved || frm.is_new()){//Check if the document is saved or new
			frappe.throw('Please Save the Document First');
		}
		else{
			let doc_name = frm.doc.name;
			if(doc_name){
				frappe.call({
					method:'one_fm.grd.doctype.pifss_monthly_deduction.pifss_monthly_deduction.import_deduction_data',
					args: {'doc_name':frm.doc.name},
					freeze: true,
					freeze_message: __("Fetching Data...."),
					callback: function(r){
					let table_data = r.message[0];
					if(!r.exc && table_data.length > 0){
					for(let i=0; i < r.message[1]; i++){
							frm.add_child('deductions', table_data[i]);
						}
					}
					frm.refresh_field('deductions');
					document.querySelectorAll("[data-fieldname='fetch_data']")[1].style.backgroundColor ="red";
					frm.set_value("press_button",1);
					frm.save();
				}
			});	
		};
	}
},
	refresh:function(frm){
		
		if (frm.doc.press_button == 0){
			document.querySelectorAll("[data-fieldname='fetch_data']")[1].style.backgroundColor ="#44c95a";
		}else{
			document.querySelectorAll("[data-fieldname='fetch_data']")[1].style.backgroundColor ="red";
		}
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
		if(frm.doc.workflow_state == 'Completed' && frm.doc.docstatus === 1){
			if (!frm.doc.pifss_monthly_deduction_tool){
				frm.add_custom_button(__('Start Pifss Monthly Deduction Tool'),
					function () {
						frappe.call({
							method: 'one_fm.grd.doctype.pifss_monthly_deduction_tool.pifss_monthly_deduction_tool.track_pifss_changes',
							args: {'pifss_monthly_deduction_name': frm.doc.name},
							callback: function(r){
								frm.set_value('pifss_monthly_deduction_tool', r.message);
								frappe.set_route("Form", "PIFSS Monthly Deduction Tool", frm.doc.pifss_monthly_deduction_tool);
					  },
					  freeze: true,
					  freeze_message: __("Creating Pifss Monthly Deduction Tracking Tool ...!")
					}).addClass('btn-primary'); 
					}
			);
		}
			else if (frm.doc.pifss_monthly_deduction_tool) {
			frm.add_custom_button(__('Go to Pifss Monthly Deduction Tracking Tool'),
				function () {
					frappe.set_route("Form", "PIFSS Monthly Deduction Tool", frm.doc.pifss_monthly_deduction_tool);
				}).addClass('btn-primary'); 
			}	
	}
		
	},
	// remaining_amount: function(frm){
	// 	if(frm.doc.remaining_amount){
	// 		frm.set_value("total_payments",frm.doc.total_sub+frm.doc.remaining_amount+frm.doc.total_additional_deduction);
	// 	}
	// },
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
	attach_invoice: function(frm){
		if(frm.doc.attach_invoice){
			frm.set_value('attached_on',frappe.datetime.now_datetime());
		}
		
	},
		
});

