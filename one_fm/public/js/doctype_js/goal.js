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
	},

	// kra: function(frm) {
	// 	if (!frm.doc.appraisal_cycle) {
	// 		frm.set_value("kra", "");

	// 		frappe.msgprint({
	// 			message: __("Please select the Appraisal Cycle first."),
	// 			title: __("Mandatory")
	// 		});

	// 		return;
	// 	}

	// 	if (frm.doc.__islocal || !frm.doc.is_group) return;

	// 	let msg = __("Modifying the KRA in the parent goal will specifically impact those child goals that share the same KRA; any other child goals with different KRAs will remain unaffected.");
	// 	msg += "<br> <br>";
	// 	msg += __("Do you still want to proceed?");

	// 	frappe.confirm(
	// 		msg,
	// 		() => {},
	// 		() => {
	// 			frappe.db.get_value("Goal", frm.doc.name, "kra", (r) => frm.set_value("kra", r.kra));
	// 		}
	// 	);
	// },
})
