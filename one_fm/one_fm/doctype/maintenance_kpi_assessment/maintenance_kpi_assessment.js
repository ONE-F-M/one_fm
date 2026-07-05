// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance KPI Assessment", {
	refresh(frm) {
		// Draft-only helper: regenerate KPI rows from the Master and re-run the
		// score calculation (useful after field technicians submit late records).
		if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.maintenance_kpi_master) {
			frm.add_custom_button(__("Rebuild & Recalculate"), () => {
				frappe.call({
					method: "one_fm.one_fm.doctype.maintenance_kpi_assessment.maintenance_kpi_assessment.rebuild_and_recalculate",
					args: { assessment: frm.doc.name },
					freeze: true,
					freeze_message: __("Recalculating KPI scores..."),
					callback() {
						frm.reload_doc();
					},
				});
			});
		}
	},
});
