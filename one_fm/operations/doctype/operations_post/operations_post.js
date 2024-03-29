// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Post', {
    refresh: (frm) => {
      frm.trigger('set_site_query');
    },
	post_template: function(frm){
		let post_template = frm.doc.post_template;
		if(post_template && post_template !== undefined){
			frappe.call({
				method:"frappe.client.get",
				args: {
					doctype: "Operations Role",
					name: post_template,
                },
				callback: function(r) {
					if(!r.exc) {
						let {designations, skills} = r.message;
						frm.clear_table("skills");
						skills.forEach((skill) => {
							let child_row = frappe.model.add_child(frm.doc, "skills");
							child_row.skill = skill.skill;
							child_row.minimum_proficiency_required = skill.minimum_proficiency_required;
						});
						frm.refresh_fields("skills");
					
						frm.clear_table("designations");
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
	},
	site_shift: (frm) => {
	    if (frm.doc.site_shift) {
            frm.set_value('post_template', '');
            frm.trigger('set_site_query');

	    }
	},
	set_site_query: (frm) => {
	    frm.set_query('post_template', () => {
            return {
                filters: {
                    shift: frm.doc.site_shift
                }
            }
        })
	}
});
