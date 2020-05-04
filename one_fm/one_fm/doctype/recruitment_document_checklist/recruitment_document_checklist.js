// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Recruitment Document Checklist', {
	refresh: function(frm) {
    frappe.meta.get_docfield("Recruitment Document", 'received', frm.doc.name).hidden = 1;
	},
  source_of_hire: function(frm) {
    set_visa_type_field_properties(frm);
  }
});

var set_visa_type_field_properties = function(frm) {
  if(frm.doc.source_of_hire == 'Local'){
    frm.set_df_property('visa_type', 'reqd', true);
  }
  else{
    frm.set_df_property('visa_type', 'reqd', false);
    frm.set_value('visa_type', '');
  }
};

frappe.ui.form.on('Recruitment Document', {
  recruitment_documents_add: function(frm, cdt, cdn) {
    var row = frappe.get_doc(cdt, cdn);
    frm.script_manager.copy_from_first_row("recruitment_documents", row, ["required_when", "type_of_copy"]);
  }
});
