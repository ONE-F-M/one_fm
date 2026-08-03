frappe.ui.form.on("Bank Account", {
	iban(frm) {
		// WI-001797: banks print an IBAN in groups of four, so a pasted value arrives
		// with grouping spaces. Strip them as the field is edited rather than waiting
		// for the save, so what the user sees is what gets stored. The server strips
		// them too, for imports and API writes that never touch this form.
		const cleaned = (frm.doc.iban || "").replace(/\s+/g, "");
		if (cleaned !== frm.doc.iban) {
			frm.set_value("iban", cleaned);
		}
	},
});
