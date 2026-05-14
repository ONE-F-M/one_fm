// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("On the Job Training", {
    setup(frm) {
        frm.set_query("employee", function () {
            return {
                filters: {
                    status: ["in", ["Active", "Vacation"]]
                }
            };
        });
    },

    refresh(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.is_extension_request) {
            frm.add_custom_button(__("OJT Extension"), function() {
                frappe.model.open_mapped_doc({
                    method: "one_fm.one_fm.doctype.on_the_job_training.on_the_job_training.create_ojt_extension",
                    frm: frm
                })
            });
        }
    },
});
