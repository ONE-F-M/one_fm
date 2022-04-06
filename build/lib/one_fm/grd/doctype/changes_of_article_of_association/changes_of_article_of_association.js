// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Changes of Article of Association', {
	refresh: function(frm) {
		var attach_changes_to_article_of_association_pdf = frappe.render_template("changes_of_article_of_association",{"doc":frm.doc});
		$(frm.fields_dict["preview_article"].wrapper).html(attach_changes_to_article_of_association_pdf);
		refresh_field("preview_article");
	},
	attach_changes_to_article_of_association: function(frm) {
		var attach_changes_to_article_of_association_pdf = frappe.render_template("changes_of_article_of_association",{"doc":frm.doc});
		$(frm.fields_dict["preview_article"].wrapper).html(attach_changes_to_article_of_association_pdf);
		refresh_field("preview_article");
	}
});
