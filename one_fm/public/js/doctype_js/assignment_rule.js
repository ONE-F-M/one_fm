frappe.ui.form.on('Assignment Rule', {
	refresh: function(frm){
		frm.add_custom_button("Set the Description", function() {
			frappe.call({
				method: 'one_fm.overrides.assignment_rule.get_assignment_rule_description',
				args: {doctype: frm.doc.document_type},
				callback: function(r) {
					console.log(r);
					if(r && r.message){
						frm.set_value('description', r.message)
					}
				}
			});
		})
	}
});
