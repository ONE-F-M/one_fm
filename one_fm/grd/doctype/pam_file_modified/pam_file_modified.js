// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

// frappe.ui.form.on('PAM File Modified', {
// 	// refresh: function(frm) {

// 	// }
// });
frappe.ui.form.on('PAM File Modified', 'refresh',{
		// total:function(frm, cdt, cdn){
		//calculate_total(frm);
	
		is_contract_file: function (frm) {

		// licence_number: function(frm) {
		if (frm.doc.is_contract_file == 1) {
			get_pam_contract_info();
		}

		else if (frm.doc.is_contract_file == 0) {
			frm.set_value("license_type", 'Members Company');
			frm.set_value("license_issuer", "Ministry of Commerce and Industry");
			frm.set_value("license_name", "One Facilities Management Company");
			frm.set_value("license_number_based_on_issuer", "m/2009/1324");
			frm.set_value("total_license_for_employment", "355");
			frm.set_value("number_of_active_permits", "0");
			frm.set_value("number_of_cancelled_permits", "44");
			frm.set_value("total_non_kuwaiti_employment", "331");
			frm.set_value("total_kuwaiti_employment", "24");
			frm.set_value("total_gcc_employment", "0");
			frm.set_value("total_other_employment", "0");
			frm.set_value("license_category", "Normal");
			frm.set_value("the_main_activity", "Public Utilities Department");
			frm.set_value("permit_category", "Third category");
			frm.set_value("table_55", "Economic Activity Table");
			frm.set_value("pam_file_number", "Private - 2921143");

		}
	},
	pam_contract_number: (frm) => {
		if (frm.doc.pam_contract_number == 'T4 - 20201800005') {
			frm.set_value("license_type", "Private Contract");
			frm.set_value("license_issuer", "Kuwait International Airport");
			frm.set_value("license_name", "Operation, management, maintenance, training, improvements and development of terminal services");
			frm.set_value("license_number_based_on_issuer", "4-2019/2018");
			frm.set_value("total_license_for_employment", "505");
			frm.set_value("number_of_active_permits", "0");
			frm.set_value("number_of_cancelled_permits", "352");
			frm.set_value("total_non_kuwaiti_employment", "483");
			frm.set_value("total_kuwaiti_employment", "22");
			frm.set_value("total_gcc_employment", "0");
			frm.set_value("total_other_employment", "0");
			frm.set_value("license_category", "Private Contract");
			frm.set_value("the_main_activity", "Airport construction contracting");
			frm.set_value("permit_category", "First category");
			frm.set_value("table_55", "Economic Activity Table");
		}
		else if (frm.doc.pam_contract_number == 'Opera - 15201800010')
			;
		{
			frm.set_value("license_type", "Private Contract");
			frm.set_value("license_issuer", "Al Diwan Al-Amiri");
			frm.set_value("license_name", "Operation and maintenance works for the facilities of the Sheikh Jaber Al-Ahmad Cultural Center");
			frm.set_value("license_number_based_on_issuer", "74/دأ/ه");
			frm.set_value("total_license_for_employment", "44");
			frm.set_value("number_of_active_permits", "0");
			frm.set_value("number_of_cancelled_permits", "16");
			frm.set_value("total_non_kuwaiti_employment", "42");
			frm.set_value("total_kuwaiti_employment", "2");
			frm.set_value("total_gcc_employment", "0");
			frm.set_value("total_other_employment", "0");
			frm.set_value("license_category", "Private Contract");
			frm.set_value("the_main_activity", "Guarding facilities by individuals");
			frm.set_value("permit_category", "First category");
			frm.set_value("table_55", "Economic Activity Table");
		}

	}
		//  total: function(frm,cdt,cdn){
		// 	calculate_total(frm);

		//  }
	});


	//pam_contract_number: get_pam_contract_info(frm) 
	
		
// 	if (frm.doc.pam_contract_number == 'T4 - 20201800005') 
// 	{
// 		frm.set_value("license_type", "Private Contract");
// 		frm.set_value("license_issuer", "Kuwait International Airport");
// 		frm.set_value("license_name", "Operation, management, maintenance, training, improvements and development of terminal services");
// 		frm.set_value("license_number_based_on_issuer", "4-2019/2018");
// 		frm.set_value("total_license_for_employment", "505");
// 		frm.set_value("number_of_active_permits", "0");
// 		frm.set_value("number_of_cancelled_permits", "352");
// 		frm.set_value("total_non_kuwaiti_employment", "483");
// 		frm.set_value("total_kuwaiti_employment", "22");
// 		frm.set_value("total_gcc_employment", "0");
// 		frm.set_value("total_other_employment", "0");
// 		frm.set_value("license_category", "Private Contract");
// 		frm.set_value("the_main_activity", "Airport construction contracting");
// 		frm.set_value("permit_category", "First category");
// 		frm.set_value("table_55", "Economic Activity Table");
// 	}
// 	else
// 		//(frm.doc.pam_contract_number == 'Opera - 15201800010');
// 	{
// 		frm.set_value("license_type", "Private Contract");
// 		frm.set_value("license_issuer", "Al Diwan Al-Amiri");
// 		frm.set_value("license_name", "Operation and maintenance works for the facilities of the Sheikh Jaber Al-Ahmad Cultural Center");
// 		frm.set_value("license_number_based_on_issuer", "74/دأ/ه");
// 		frm.set_value("total_license_for_employment", "44");
// 		frm.set_value("number_of_active_permits", "0");
// 		frm.set_value("number_of_cancelled_permits", "16");
// 		frm.set_value("total_non_kuwaiti_employment", "42");
// 		frm.set_value("total_kuwaiti_employment", "2");
// 		frm.set_value("total_gcc_employment", "0");
// 		frm.set_value("total_other_employment", "0");
// 		frm.set_value("license_category", "Private Contract");
// 		frm.set_value("the_main_activity", "Guarding facilities by individuals");
// 		frm.set_value("permit_category", "First category");
// 		frm.set_value("table_55", "Economic Activity Table");
// 	}
	
// }
// var calculate_total = function(frm, cdt, cdn){
// 	var child = locals[cdt][cdn];
// 	frappe.model.set_value(child.doctype, child.name, 'total', child.inside + child.outside);
// }

// calculate_total(frm, cdt,cdn)
// {
// 	var child = locals[cdt][cdn];
// 	frappe.model.set_value(child.doctype, child.name, 'total', child.inside + child.outside);
// }