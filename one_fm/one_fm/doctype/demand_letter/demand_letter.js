// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Demand Letter', {
	refresh: function(frm) {
		frm.set_query('agency_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Agency',
					'link_name': frm.doc.agency
				}
			}
		})
	},
	terms_and_condition_template: function(frm) {
    set_terms_and_condition(frm);
	},
	agency_address: function(frm) {
		set_agency_address(frm);
	},
	pam_file: function(frm) {
		set_authorized_signatory(frm);
	}
});

var set_authorized_signatory = function(frm) {
	let options = [];
	if(frm.doc.pam_file){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'PAM Authorized Signatory List',
				filters: {'pam_file_name': frm.doc.pam_file}
			},
			callback: function(r) {
				if(r.message && r.message.authorized_signatory){
					var signatory_list = r.message.authorized_signatory;
					options[0] = '';
					signatory_list.forEach((item, i) => {
						options[i+1] = item.authorized_signatory_name_english;
					});
					frm.set_df_property('authorized_signatory', 'options', options);
					if(options.length == 2){
						frm.set_value('authorized_signatory', options[1]);
					}
				}
			}
		});
	}
	else{
		frm.set_df_property('authorized_signatory', 'options', options);
	}
};

var set_agency_address = function(frm) {
	if(frm.doc.agency_address){
		frappe.call({
			method: 'frappe.contacts.doctype.address.address.get_address_display',
			args: {
				"address_dict": frm.doc.agency_address
			},
			callback: function(r) {
				frm.set_value("complete_adress", r.message);
			}
		});
	}
	if(!frm.doc.agency_address){
		frm.set_value("complete_adress", "");
	}
};

var set_terms_and_condition = function(frm) {
  if(frm.doc.terms_and_condition_template){
    frm.clear_table('recruitment_terms_and_condition');
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'Recruitment Terms and Condition Template',
        filters: {
          name: frm.doc.terms_and_condition_template
        }
      },
      callback: function(r) {
        if(r && r.message && r.message.recruitment_terms_and_condition){
          let options = r.message.recruitment_terms_and_condition;
          options.forEach((option) => {
          	let terms = frappe.model.add_child(frm.doc, 'Recruitment Terms and Condition', 'recruitment_terms_and_condition');
            frappe.model.set_value(terms.doctype, terms.name, 'terms', option.terms);
            frappe.model.set_value(terms.doctype, terms.name, 'conditions', option.conditions);
        	});
        }
        frm.refresh_field('recruitment_terms_and_condition');
      }
    });
		frm.refresh_field('recruitment_terms_and_condition');
  }
};
