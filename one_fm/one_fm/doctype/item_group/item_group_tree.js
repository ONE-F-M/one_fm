frappe.treeview_settings["Item Group"] = {
	ignore_fields:["parent_item_group","item_group_code","is_group"],
	onrender: function(node) {
		$("div[data-fieldname='is_group']").addClass('hide');
	}
}