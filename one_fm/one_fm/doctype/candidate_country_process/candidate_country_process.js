// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Candidate Country Process', {
  agency_country_process: function(frm) {
    set_country_process_details(frm);
  },
  refresh:  function(frm){
    candidate_country_process_flow_btn(frm);
	}
});

var set_country_process_details = function(frm) {
  if(frm.doc.agency_country_process){
    frm.doc.agency_process_details = [];
    frappe.model.with_doc("Agency Country Process", frm.doc.agency_country_process, function() {
      var agency_country_process= frappe.model.get_doc("Agency Country Process", frm.doc.agency_country_process)
      $.each(agency_country_process.agency_process_details, function(index, row){
        var d = frm.add_child("agency_process_details");
        d.process_name = row.process_name;
        d.responsible = row.responsible;
        d.duration_in_days = row.duration_in_days;
        d.attachment_required = row.attachment_required;
        d.notes_required = row.notes_required;
        d.reference_type = row.reference_type;
        d.reference_complete_status_field = row.reference_complete_status_field;
				d.reference_complete_status_value = row.reference_complete_status_value;
        d.expected_date = frappe.datetime.add_days(frm.doc.start_date, row.duration_in_days);
      });
      frm.refresh_field("agency_process_details");
    });
  }
};

var candidate_country_process_flow_btn = function(frm) {
  if(!frm.doc.__islocal && frm.doc.name){
    frappe.call({
      doc: frm.doc,
      method:"get_workflow",
      callback: function(data){
        if(!data.exc){
          var workflow_list = data.message;
          workflow_list.forEach(function(workflow_doctype, i) {
            if(frm.doc.doctype != workflow_doctype.doctype){
              frm.add_custom_button(__(workflow_doctype.doctype), function() {
                if (!("new_doc" in workflow_doctype)){
                  var doclist = frappe.model.sync(workflow_doctype);
                  frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                }
                else{
                  frappe.route_options = {
                    "candidate_country_process": frm.doc.name
                  };
                  frappe.new_doc(workflow_doctype.doctype);
                }
              },__("Country Process Flow"));
            }
          });
        }
      }
    });
  }
};
