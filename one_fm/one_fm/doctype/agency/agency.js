// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agency', {
	refresh: function(frm) {
    set_address_and_contact_html(frm);
    frm.set_df_property('attachments_required_section', 'hidden', frm.doc.__islocal);
	},
	agency_website: function(frm) {
		validate_website_adress(frm);
	}
});

var validate_website_adress = function(frm) {
	if(frm.doc.agency_website){
		frappe.call({
			method: 'one_fm.one_fm.doctype.agency.agency.validate_website_adress',
			args: {website: frm.doc.agency_website},
			callback: function(r) {
				if(r && !r.message){
					frappe.throw(__("The Given Website Address is not Valid."));
				}
			}
		});
	}
};

var set_address_and_contact_html = function(frm) {
  frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Agency'}
  frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

  if(!frm.doc.__islocal) {
    frappe.contacts.render_address_and_contact(frm);
  } else {
    frappe.contacts.clear_address_and_contact(frm);
  }
};
