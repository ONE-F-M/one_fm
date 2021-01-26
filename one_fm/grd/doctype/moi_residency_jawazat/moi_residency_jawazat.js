// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MOI Residency Jawazat', {
	refresh: function(frm) {

	},
	onload: function(frm) {
		if(frm.doc.__islocal){
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"PAM File",
					filters: {
						name:"ONE FM Hawally Private File"
					},
					fieldname:["pam_file_number","company_unified_number","pam_file_governorate_arabic"]
				}, 
				callback: function(r) { 
			
					// set the returned value in a field
					frm.set_value('company_pam_file_number', r.message.pam_file_number);
					frm.set_value('company_centralized_number', r.message.company_unified_number);
					frm.set_value('governorate', r.message.pam_file_governorate_arabic);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"MOCI License",
					filters: {
						name:"ONE Facilities Management Company W.L.L."
					},
					fieldname:["license_trade_name_arabic","street","building"]
				}, 
				callback: function(r) { 
			
					// set the returned value in a field
					frm.set_value('company_trade_name', r.message.license_trade_name_arabic);
					frm.set_value('company_street_name', r.message.street);
					frm.set_value('company_building_name', r.message.building);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"Company",
					filters: {
						name:"ONE Facilities Management"
					},
					fieldname:["email","phone_no"]
				}, 
				callback: function(r) { 
			
					// set the returned value in a field
					frm.set_value('company_email_id', r.message.email);
					frm.set_value('company_contact_number', r.message.phone_no);
				}
			})
			frappe.call({
				method:"frappe.client.get_value",
				args: {
					doctype:"PACI Number",
					filters: {
						name:"ONE Facilities Management"
					},
					fieldname:["paci_number","area_name","block"]
				}, 
				callback: function(r) { 
			
					// set the returned value in a field
					frm.set_value('paci_number', r.message.paci_number);
					frm.set_value('company_location', r.message.area_name);
					frm.set_value('company_block_number', r.message.block);
					
					
				}
			})
		}
		
	}
});
