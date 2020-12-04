frappe.ui.form.on('Item', {
	refresh(frm) {
		frm.set_query("subitem_group", function() {
			return {
				filters: [
					['Item Group', 'parent_item_group', '=', cur_frm.doc.parent_item_group]
				]
			};
		});

		frm.set_query("item_group", function() {
			return {
				filters: [
					['Item Group', 'parent_item_group', '=', cur_frm.doc.subitem_group]
				]
			};
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
						console.log(r.message)
						var new_item_id = String(parseInt(r.message)+1)
						console.log(new_item_id)
						var final_item_id = new_item_id.padStart(4, '0')
						console.log(final_item_id)
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
					if(ret && ret.message){
						frm.clear_table('item_descriptions');
					  if(ret.message.one_fm_item_group_descriptions){
					    ret.message.one_fm_item_group_descriptions.forEach((item, i) => {
					      let desc = frappe.model.add_child(frm.doc, 'Item Description', 'item_descriptions');
					      frappe.model.set_value(desc.doctype, desc.name, 'description_attribute', item.description_attribute);
					    });
					  }
					  frm.refresh_field('item_descriptions');
					}
				}
			});
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
