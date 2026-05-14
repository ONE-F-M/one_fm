// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Candidate Country Process', {
  agency_country_process: function(frm) {
    set_country_process_details(frm);
  },
  refresh:  function(frm){
    candidate_country_process_flow_btn(frm);
    calculate_live_plan_eta(frm);
    
    if (frm.doc.agency_country_process && !frm.doc.__islocal) {
        frm.add_custom_button(__("Sync Process Steps"), function() {
            frappe.confirm('Are you sure you want to sync missing steps from the Agency Process? This will keep your existing progress safe.', function() {
                frappe.model.with_doc("Agency Country Process", frm.doc.agency_country_process, function() {
                    var agency_doc = frappe.model.get_doc("Agency Country Process", frm.doc.agency_country_process);
                    var existing_processes = {};
                    
                    // Backup existing rows by process name
                    (frm.doc.agency_process_details || []).forEach(row => {
                        existing_processes[row.process_name] = row;
                    });
                    
                    frm.clear_table("agency_process_details");
                    
                    $.each(agency_doc.agency_process_details, function(index, source_row){
                        var d = frm.add_child("agency_process_details");
                        // Copy baseline structure from Agency Process
                        d.process_name = source_row.process_name;
                        d.responsible = source_row.responsible;
                        d.duration_in_days = source_row.duration_in_days;
                        d.attachment_required = source_row.attachment_required;
                        d.notes_required = source_row.notes_required;
                        d.reference_type = source_row.reference_type;
                        d.reference_complete_status_field = source_row.reference_complete_status_field;
                        d.reference_complete_status_value = source_row.reference_complete_status_value;
                        if (frm.doc.start_date && source_row.duration_in_days) {
                            d.expected_date = frappe.datetime.add_days(frm.doc.start_date, source_row.duration_in_days);
                        }
                        
                        // Restore previous progress if the row already existed
                        if (existing_processes[source_row.process_name]) {
                            var old_row = existing_processes[source_row.process_name];
                            d.status = old_row.status;
                            d.actual_date = old_row.actual_date;
                            d.notes = old_row.notes;
                            d.reference_name = old_row.reference_name;
                        }
                    });
                    
                    frm.refresh_field("agency_process_details");
                    frappe.msgprint(__("Successfully synced. The table has been updated with the correct 11 rows. Please hit Save!"));
                });
            });
        });
    }
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
      
      if (frm.doc.start_date && agency_country_process.total_duration) {
          frm.set_value('planned_eta', frappe.datetime.add_days(frm.doc.start_date, agency_country_process.total_duration));
          frm.set_value('live_plan_eta', frm.doc.planned_eta);
      }
    });
  }
};

var calculate_live_plan_eta = function(frm) {
    if (!frm.doc.planned_eta) return;
    
    var total_delay = 0;
    (frm.doc.agency_process_details || []).forEach(row => {
        if (row.actual_date && row.expected_date) {
            var delay_days = frappe.datetime.get_day_diff(row.actual_date, row.expected_date);
            total_delay += delay_days;
        }
    });
    
    var new_live_eta = frappe.datetime.add_days(frm.doc.planned_eta, total_delay);
    if (frm.doc.live_plan_eta !== new_live_eta) {
        frm.set_value('live_plan_eta', new_live_eta);
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
