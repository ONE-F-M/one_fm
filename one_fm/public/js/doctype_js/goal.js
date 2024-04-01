frappe.ui.form.on("Goal", {
	refresh(frm) {
		frm.set_query("parent_goal", () => {
			return {
				filters: {
					is_group: 1,
					name: ["!=", frm.doc.name]
				}
			}
		});
	}
})
