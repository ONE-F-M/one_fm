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

	party_type(frm) {
		frm.trigger("party");
	},

	party(frm) {
		// WI-004063: fill the Civil ID from the Employee record. Done here rather
		// than with fetch_from, which would query a one_fm_civil_id column on
		// every party type and break for Supplier/Customer. Only set a value the
		// Employee really has, so a manually typed Civil ID is never wiped.
		if (frm.doc.party_type !== "Employee" || !frm.doc.party) {
			return;
		}
		const party = frm.doc.party;
		frappe.db.get_value("Employee", party, "one_fm_civil_id").then((r) => {
			const civil_id = r && r.message && r.message.one_fm_civil_id;
			// ignore a late answer if the user has already picked another employee
			if (civil_id && frm.doc.party === party && frm.doc.civil_id !== civil_id) {
				frm.set_value("civil_id", civil_id);
			}
		});
	},
});
