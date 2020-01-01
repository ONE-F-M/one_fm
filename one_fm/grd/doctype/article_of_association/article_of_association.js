// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Article Of Association', {
	refresh: function(frm) {
		var article_of_association_pdf = frappe.render_template("article_of_association",{"doc":frm.doc});
		$(frm.fields_dict["preview_article"].wrapper).html(article_of_association_pdf);
		refresh_field("preview_article");
	},
	article_of_association: function(frm) {
		var article_of_association_pdf = frappe.render_template("article_of_association",{"doc":frm.doc});
		$(frm.fields_dict["preview_article"].wrapper).html(article_of_association_pdf);
		refresh_field("preview_article");
	}
});
