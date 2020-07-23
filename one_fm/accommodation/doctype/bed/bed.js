// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bed', {
	refresh: function(frm) {
		frm.set_query('accommodation_space', function () {
			return {
				filters: {
					'bed_space_available': 1
				}
			};
		});
		if(!frm.is_new() && frm.doc.status == 'Vacant'){
			var book_bed_btn = frm.add_custom_button(__('Book Bed'), function() {
				book_bed(frm);
			});
			book_bed_btn.addClass('btn-primary');
		}
	}
});

var book_bed = function(frm) {
  frappe.route_options = {"bed": frm.doc.name};
	frappe.new_doc("Book Bed");
};
