frappe.pages['roster'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'None',
		single_column: true
	});
	$(wrapper).closest('.page-container').empty().append(frappe.render_template('roster'));

}