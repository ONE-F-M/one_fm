frappe.ui.form.on('Asset Movement', {
    onload: function(frm) {
        frm.set_query('asset', 'assets', function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: {
                    'item_code': row.rfm_item_code,
                    'status': ["not in", ["Draft"]]
                }
            };
        });
    },
    before_workflow_action: function(frm) {
        const action = frm.selected_workflow_action;

        // Only the assigned incoming employee may receive or reject the handover.
        if (["Receive Asset", "Reject Asset"].includes(action)
            && frm.doc.custom_handover_employee_user
            && frappe.session.user !== frm.doc.custom_handover_employee_user) {
            frappe.throw(__("Only the assigned incoming employee can receive or reject this asset handover."));
        }

        // A reason must be provided before rejecting.
        if (action === "Reject Asset" && !frm.doc.custom_reason_for_rejection) {
            frappe.throw(__("Please select a Reason for Rejection before rejecting the asset handover."));
        }
    }
});
