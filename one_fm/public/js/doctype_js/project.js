frappe.ui.form.on('Project', {
    refresh(frm) {
        frm.set_df_property('project_type', 'reqd', true);
        if (frm.doc.project_type === "External") {
            const poc_field = cur_frm.get_field("poc").grid;
            poc_field.toggle_reqd("poc", true);
            poc_field.toggle_reqd("designation", true);
        }
        frm.set_query("income_account", () => ({
            filters: { root_type: 'Income', is_group: 0 }
        }));
        frm.set_query("cost_center", () => ({
            filters: { is_group: 0 }
        }));
        frm.refresh_field("income_account");
        frm.refresh_field("cost_center");
    },
    before_save(frm) {
        validate_linked_schedules(frm);
    }
});

function validate_linked_schedules(frm) {
    if (frm.doc.is_active === 'No' && !frm.__confirmed_inactive && !frm.is_new()) {
        frappe.call({
            method: "one_fm.one_fm.project_custom.check_existing_schedules",
            args: {
                project: frm.doc.name
            },
            callback(response) {
                if (response.message && response.data_obj && response.data_obj.is_exist) {
                    frappe.confirm(
                        "The future Employee Schedules linked to the Project will be deleted on confirmation. Do you want to proceed?",
                        function () {
                            frappe.call({
                                method: "one_fm.one_fm.project_custom.delete_future_schedules",
                                args: {
                                    project: frm.doc.name
                                },
                                freeze: true,
                                freeze_message: __("Deleting Linked Schedules..."),
                                callback: function() {
                                    frm.__confirmed_inactive = true;
                                    frm.save();
                                }
                            });
                        },
                        function () {
                            frappe.validated = false;
                            frm.reload_doc();
                        }
                    );
                } else {
                    frappe.validated = true;
                }
            }
        });
        frappe.validated = false;
    }
}
