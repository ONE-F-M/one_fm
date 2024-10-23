frappe.ui.form.on("Leave Application", {
    before_workflow_action: function(frm) {
        if (frm.selected_workflow_action === 'Propose New Date') {
            
            // Create a custom modal using frappe.ui.Dialog
            let dialog = new frappe.ui.Dialog({
                title: 'Confirm New Dates',
                fields: [
                    {
                        fieldtype: 'Date', 
                        fieldname: 'custom_propose_from_date', 
                        label: 'Proposed From Date', 
                        default: frm.doc.custom_propose_from_date, 
                        reqd: 1,
                        change: function() {
                            calculate_days(dialog); // Trigger calculation when date changes
                        }
                    },
                    {
                        fieldtype: 'Date', 
                        fieldname: 'custom_propose_to_date', 
                        label: 'Proposed To Date', 
                        default: frm.doc.custom_propose_to_date, 
                        reqd: 1,
                        change: function() {
                            calculate_days(dialog); // Trigger calculation when date changes
                        }
                    },
                    {
                        fieldtype: 'Data', 
                        fieldname: 'custom_total_propose_leave_days', 
                        label: 'Number of Days', 
                        read_only: 1,
                        default: '0' // Initially set to 0
                    }
                ],
                primary_action_label: 'Confirm',
                primary_action(values) {
                    // Fetch the new values from the dialog before validation
                    let from_date = values.custom_propose_from_date;
                    let to_date = values.custom_propose_to_date;
                    let total_days = dialog.get_value('custom_total_propose_leave_days');
                    let is_valid = validate_proposeddate(frm,from_date, to_date,dialog);
                    if (is_valid) {
                        frm.set_value('custom_propose_from_date', from_date);
                        frm.set_value('custom_propose_to_date', to_date);
                        frm.set_value('custom_total_propose_leave_days', total_days);
                        dialog.hide();
                        frm.save().then(() => {
                            frappe.msgprint("New Dates Proposed successfully");
                            frappe.call({
                                method: "one_fm.overrides.leave_application.send_proposed_date_email",
                                args: {
                                    doc_name: frm.doc.name
                                },
                                callback: function(response) {
                                    if (response.message === "success") {
                                        frappe.msgprint("Email sent successfully.");
                                    }
                                }
                            });
                        });
                    }
                }
            });
            dialog.show();
        }
    },  
    refresh: function(frm) {
        // frm.set_intro("Please save the form after adding a new row to the Proof Documents table before attaching the document")
        if (!frm.is_new()){
            frappe.call({
                method: 'one_fm.utils.enable_edit_leave_application',
                args: {
                    doc: frm.doc
                },
                callback: function(r) {
                    var fields = ['is_proof_document_required', 'from_date','to_date','leave_approver']
                    for (var i in fields){
                        if (r && r.message) {
                            cur_frm.set_df_property(fields[i],  'read_only', 0);
                        }
                        else{
                            cur_frm.set_df_property(fields[i],  'read_only', 1);
                            cur_frm.set_df_property(fields[i],  'read_only_depends_on', "eval:doc.workflow_state=='Open' || doc.workflow_state=='Approved' || doc.workflow_state=='Rejected'");
                        }
                    }

                }
            })
            // check approvers
            if(frm.doc.workflow_state=='Open' && frappe.session.user!=frm.doc.leave_approver){
                $('.actions-btn-group').hide();
            }
            if (frm.doc.workflow_state=='Open' && frappe.user.has_role('HR Manager')){
                $('.actions-btn-group').show();
                // $('.btn .btn-primary .btn-sm').show();
            }
        }
        if (frm.doc.status == 'Approved' && frm.doc.__onload && frm.doc.__onload.attendance_not_created){
          frm.add_custom_button(__('Update Attendance'),
            function () {
              frappe.call({
                doc: frm.doc,
                method: 'update_attendance',
                callback: function(r) {
                  frm.reload_doc();
                }
              });
            }
          );
        }
    },
    onload: function(frm) {
        $.each(frm.fields_dict, function(fieldname, field) {
          field.df.onchange = frm =>{
            if (cur_frm.doc.employee && cur_frm.doc.leave_type == "Sick Leave"){
                frappe.db.get_value("Employee", cur_frm.doc.employee, "is_in_kuwait").then(res=>{
                    res.message.is_in_kuwait ? cur_frm.set_value("is_proof_document_required", 1) : cur_frm.set_value("is_proof_document_required", 0)
                    cur_frm.refresh_field("is_proof_document_required")

                })
            }
          };
        });
        prefillForm(frm);
      },
    validate: function(frm) {
        validate_reliever(frm);
    },
    custom_reliever_: function(frm){
        validate_reliever(frm);
    }
})


var prefillForm = frm => {
    const url = new URL(window.location.href);

    const params = new URLSearchParams(url.search);

    const doc_id = params.get('doc_id');
    const doctype = params.get('doctype');

    if (doctype == "Attendance Check"){
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                'doctype': doctype,
                'filters': {'name': doc_id},
                'fieldname': [
                    "employee"
                ]
            },
            callback: function(r) {
                if (r.message) {
                    cur_frm.set_value("employee", r.message.employee)

                }
            }
        });
    }

}


var validate_reliever = (frm) => {
    if (frm.doc.custom_reliever_){
        if (frm.doc.custom_reliever_ == frm.doc.employee){
            frappe.throw("Oops! You can't assign yourself as the reliever!")
        }
    }
}

var calculate_days = (dialog) => {
    let from_date = dialog.get_value('custom_propose_from_date');
    let to_date = dialog.get_value('custom_propose_to_date');
    if (from_date && to_date) {
        let days_diff = frappe.datetime.get_diff(to_date, from_date);
        if (days_diff >= 0) {
            dialog.set_value('custom_total_propose_leave_days', days_diff);
        } else {
            dialog.set_value('custom_total_propose_leave_days', '0');
        }
    } else {
        dialog.set_value('custom_total_propose_leave_days', '0');
    }
}

var validate_proposeddate =(frm,from_date, to_date,dialog)=>{
    let custom_total_propose_leave_days =  dialog.get_value('custom_total_propose_leave_days'),
    validate_annual_leave = frappe.db.get_value("Leave Type", frm.doc.leave_type, "one_fm_is_paid_annual_leave")
    
    if (frappe.datetime.get_diff(to_date, from_date) < 0) {
        frappe.throw("Proposed From Date cannot be later than the To Date");
        return false;
    }
    if (frappe.datetime.get_diff(from_date, frappe.datetime.now_date()) < 0) {
        frappe.throw("Proposed From Date cannot be in the past.");
        return false;
    }
    if (validate_annual_leave && frm.doc.total_leave_days >= 15){
        if (custom_total_propose_leave_days < 15){
            frappe.throw("You are not allowed to reduce the total leave days below 15 days. Please propose another period.")}
    }
    return true; // Validation passed
    
    }