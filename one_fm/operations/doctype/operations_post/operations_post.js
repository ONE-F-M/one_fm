// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Post', {
	post_template: function(frm){
		let post_template = frm.doc.post_template;
		if(post_template !== undefined){
			frappe.call({
				method:"frappe.client.get",
				args: {
					doctype: "Post Type",
					name: post_template,
                },
				callback: function(r) {
					if(!r.exc) {
						let {designations, skills} = r.message;
						skills.forEach((skill) => {
							let child_row = frappe.model.add_child(frm.doc, "skills");
							child_row.skill = skill.skill;
							child_row.minimum_proficiency_required = skill.minimum_proficiency_required;
						});
						frm.refresh_fields("skills");
						designations.forEach((designation) => {
							let child_row = frappe.model.add_child(frm.doc, "designations");
							child_row.designation = designation.designation;
							child_row.primary = designation.primary;
						});										
						frm.refresh_fields("designations");
					}
				}
			});
		}
	}
});


frappe.ui.form.on('Operations Post', {
	refresh: function(frm){}
})