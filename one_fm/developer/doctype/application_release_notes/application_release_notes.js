// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Application Release Notes', {
	refresh: function(frm) {
		frm.disable_save();
		frm.trigger('show_release_as_html');
	},
	show_release_as_html: function(frm) {
		// Initialise showdown to convert markdown to html
		var converter = new showdown.Converter();
		frm.set_value('release_notes', converter.makeHtml(frm.doc.release_notes));
		// frm.set_value('')
	}
});
