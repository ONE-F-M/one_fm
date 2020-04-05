frappe.pages['face-recognition'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Face Recognition',
		single_column: true
	});
}