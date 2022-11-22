frappe.ui.form.on("Leave Application", {
    refresh: function(frm) {
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
                $('.btn.btn-primary.btn-sm').hide();
            }
            if (frm.doc.workflow_state=='Open' && frappe.user.has_role('HR Manager')){
                $('.btn.btn-primary.btn-sm').show();
            }
        }

    }
})


frappe.ui.form.on("Proof Documents",{
    refresh:(frm,cdt,cdn)=>{
        frm.set_intro("Please save the form after adding each row before attaching the proof")
    },
    // This ensures that the attachment field is not shown until the row is saved
    proof_documents_add:function(frm,cdt,cdn) {
        if(cdn.includes('new')){
            frm.fields_dict.proof_documents.grid.toggle_display('attachments',false)
        }
    }
})
