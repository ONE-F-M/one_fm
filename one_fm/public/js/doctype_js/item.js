frappe.ui.form.on('Item', {
	refresh(frm) {
		frm.set_query("subitem_group", function() {
			return {
				filters: [
					['Item Group', 'parent_item_group', '=', cur_frm.doc.parent_item_group]
				]
			};
		});

		frm.set_query("value", "item_descriptions", function(doc, cdt, cdn) {
			var child = locals[cdt][cdn];
			return {
				query: "one_fm.purchase.utils.filter_description_specific_for_item_group",
				filters: {'doctype': child.description_attribute, 'item_group': doc.subitem_group}
			};
		});

		frm.set_query("item_group", function() {
			return {
				filters: [
					['Item Group', 'parent_item_group', '=', cur_frm.doc.subitem_group]
				]
			};
		});
		frm.set_query("uniform_type_description", function() {
			return {
				query: "one_fm.utils.filter_uniform_type_description",
				filters: {'uniform_type': frm.doc.uniform_type}
			}
		});
	},
	validate: function(frm){
		frm.set_value("item_barcode", cur_frm.doc.item_code)
		var final_description = ""
		if(frm.doc.one_fm_project){
			final_description+=frm.doc.one_fm_project
		}
		if(frm.doc.one_fm_designation){
			final_description+=(final_description?' - ':'')+frm.doc.one_fm_designation
		}
		if(frm.doc.uniform_type){
			final_description+=(final_description?' - ':'')+frm.doc.uniform_type
		}
		if(frm.doc.uniform_type_description){
			final_description+=(final_description?' - ':'')+frm.doc.uniform_type_description
		}
		frm.doc.item_descriptions.forEach((item, i) => {
			final_description+=(final_description?' - ':'')+item.value
		});
		if(frm.doc.other_description){
			final_description+=(final_description?' - ':'')+frm.doc.other_description
		}
		frm.set_value("description", final_description);
	},
	parent_item_group: function(frm) {
		if(cur_frm.doc.parent_item_group){
			frm.set_value('subitem_group', '');
			frm.set_value('item_group', '');
			get_item_code(frm);
		}
	},
	subitem_group: function(frm) {
		if(cur_frm.doc.parent_item_group){
			frm.set_value('item_group', '');
			get_item_code(frm);
		}
	},
	item_group: function(frm) {
		if(cur_frm.doc.parent_item_group){
			get_item_code(frm);
		}
		if(cur_frm.doc.item_group && cur_frm.doc.subitem_group && cur_frm.doc.parent_item_group){
			frm.call({
				method: "one_fm.utils.get_item_id_series",
				args: {
					"parent_item_group": cur_frm.doc.parent_item_group,
					"subitem_group": cur_frm.doc.subitem_group,
					"item_group": cur_frm.doc.item_group
				},
				callback: function(r) {
					if(r.message){
						var new_item_id = String(parseInt(r.message)+1)
						var final_item_id = new_item_id.padStart(6, '0')
						frm.set_value("item_id", final_item_id)
					}
				}
			})
		}
		if(frm.doc.item_group){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Item Group',
					filters: {'name': frm.doc.item_group}
				},
				callback: function(ret) {
					frm.set_value('have_uniform_type_and_description', false);
					frm.clear_table('item_descriptions');
					if(ret && ret.message){
						if(ret.message.is_fixed_asset){
							frm.set_value('is_fixed_asset', ret.message.is_fixed_asset);
							frm.set_value('asset_category', ret.message.asset_category);
						}
					  if(ret.message.one_fm_item_group_descriptions){
					    ret.message.one_fm_item_group_descriptions.forEach((item, i) => {
								if(item.description_attribute == "Uniform Type" || item.description_attribute == "Uniform Type Description"){
									frm.set_value('have_uniform_type_and_description', true);
								}
								else{
									let desc = frappe.model.add_child(frm.doc, 'Item Description', 'item_descriptions');
						      frappe.model.set_value(desc.doctype, desc.name, 'description_attribute', item.description_attribute);
								}
					    });
					  }
					}
					frm.refresh_field('item_descriptions');
				}
			});
		}
		else{
			frm.set_value('have_uniform_type_and_description', false);
			frm.clear_table('item_descriptions');
			frm.refresh_field('item_descriptions');
		}
	},
	item_id: function(frm) {
		if(cur_frm.doc.item_id){
			get_item_code(frm);
		}
	}
})

function get_item_code(frm){
	frm.set_value('item_code','')
	frappe.call({
		method: "one_fm.utils.get_item_code",
		args: {
			'parent_item_group': cur_frm.doc.parent_item_group,
			'subitem_group': cur_frm.doc.subitem_group,
			'item_group': cur_frm.doc.item_group,
			'cur_item_id': cur_frm.doc.item_id
		},
		callback: function (r) {
			if (r.message) {
				frm.set_value('item_code', r.message)
				frm.set_value('item_barcode', r.message)
			}
		}
	});
}
