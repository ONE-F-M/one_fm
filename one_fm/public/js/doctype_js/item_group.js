frappe.ui.form.on('Item Group', {
	parent_item_group: function(frm) {
		if(frm.doc.parent_item_group){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Item Group',
					filters: {'name': frm.doc.parent_item_group}
				},
				callback: function(ret) {
					if(ret && ret.message){
						frm.set_value('is_fixed_asset', ret.message.is_fixed_asset);
						if(ret.message.is_fixed_asset && ret.message.asset_category && !frm.doc.asset_category){
							frm.set_value('asset_category', ret.message.asset_category);
						}
						frm.clear_table('one_fm_item_group_descriptions');
					  if(ret.message.one_fm_item_group_descriptions){
					    ret.message.one_fm_item_group_descriptions.forEach((item, i) => {
					      let desc = frappe.model.add_child(frm.doc, 'Item Group Description', 'one_fm_item_group_descriptions');
					      frappe.model.set_value(desc.doctype, desc.name, 'description_attribute', item.description_attribute);
								frappe.model.set_value(desc.doctype, desc.name, 'from_parent', true);
					    });
					  }
					  frm.refresh_field('one_fm_item_group_descriptions');
					}
				}
			});
		}
	},
	one_fm_item_group_abbr: function(frm) {
		var description = "";
		if(frm.doc.one_fm_item_group_abbr){
			// check if abbreviation exists
			frappe.db.get_value(
				"Item Group", {"one_fm_item_group_abbr": frm.doc.one_fm_item_group_abbr}, "one_fm_item_group_abbr",
				(val) => {
					if (val && val.one_fm_item_group_abbr) {
						description = __("{0} already exists. Select another abbreviation", [val.one_fm_item_group_abbr])
					}
					frm.set_df_property("one_fm_item_group_abbr", "description", description);
				}
			);
		}
		else{
			frm.set_df_property("one_fm_item_group_abbr", "description", description);
		}
	}
});

// frappe.ui.form.on('Item Group Description', {
// 	one_fm_item_group_descriptions_remove: function(frm, cdt, cdn) {
// 		frappe.msgprint(__("Not permitted, configure Item Group as required"));
// 		cur_frm.reload_doc();
// 	}
// });
