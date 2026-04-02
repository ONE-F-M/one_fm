// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Temporary Deployment", {
    refresh(frm) {
        // Hide the (+) button for Temporary Post in the form's Connections dashboard section.
        // The connections section (rendered from the DocType's `links` array) lives in
        // frm.dashboard.wrapper — run immediately and after a delay for async rendering.
        function hide_new_btn() {
            frm.dashboard.wrapper
                .find('[data-doctype="Temporary Post"]')
                .find('.btn-new-doc, .btn-new, .link-new-doc')
                .hide();
        }
        hide_new_btn();
        setTimeout(hide_new_btn, 500);
    }
});
