frappe.listview_settings['Employee Checkin'] = {
	onload: function(doc) {
		if (!frappe.user.has_role('System Manager')){
		    $('.btn.btn-primary.btn-sm.primary-action').hide();
		}
	}
};
