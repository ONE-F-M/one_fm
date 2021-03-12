// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checkpoints', {
	refresh: function(frm) {
		var qr_code = frappe.render_template("qr_code",{"doc":frm.doc});
        $(frm.fields_dict["checkpoint_qr"].wrapper).html(qr_code);
        refresh_field("checkpoint_qr")
	},

	setup: function(frm) {
		frm.set_query("project_name", function() {
			return {
				filters: {
					"project_type": 'External'
				}
					
				
			}
		});

		frm.set_query("site_name", function() {
			return {
				filters: {
					"project_name": frm.doc.project_name
				}
					
				
			}
		});

	}
});

