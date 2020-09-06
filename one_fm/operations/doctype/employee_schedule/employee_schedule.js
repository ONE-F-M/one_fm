// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Schedule', {
	shift : function(frm) {
		let {shift} = frm.doc;
		if(shift){
			frm.set_query("post_type", function() {
				return {
					query: "one_fm.operations.doctype.employee_schedule.employee_schedule.get_post_types",
					filters: {shift}
				};
			});
			
		}
	}
});