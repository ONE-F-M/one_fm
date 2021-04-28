frappe.ui.form.on('Item', {
	refresh(frm) {
		set_item_field_property(frm);
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
		frm.set_query("item_type", function() {
			return {
				filters: [
					['Item Type', 'item_group', '=', cur_frm.doc.subitem_group]
				]
			};
		});
		frm.set_query("item_model", function() {
			return {
				filters: [
					['Item Model', 'item_brand', '=', cur_frm.doc.item_brand]
				]
			};
		});
		var fields = ["item_link"];
		for ( var i=0; i< fields.length; i++ ){
			//console.log("here");
			frm.set_query(fields[i], function(){
				return{
					filters: [
						['Item', 'subitem_group', '=', cur_frm.doc.subitem_group]
					]
				}
			});
		}
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
		// Item life: Date block 
		if(frm.doc.subitem_group == 'Service'){
			frm.set_value('is_service', true);
			frm.set_df_property('start_date', 'reqd', true);
			frm.set_df_property('end_date', 'reqd', true);
			frm.set_df_property('item_brand', 'reqd', false);
			frm.set_df_property('item_model', 'reqd', false);
			frm.set_df_property('item_material', 'reqd', false);
			frm.set_df_property('item_area_of_use', 'reqd', false);
			frm.set_df_property('item_color', 'reqd', false);
			frm.set_df_property('item_uom', 'reqd', false);
		}
		else if(frm.doc.subitem_group == 'Uniform' || frm.doc.subitem_group == 'Bedding'){
			frm.set_value('is_service', true);
			frm.set_df_property('start_date', 'reqd', false);
			frm.set_df_property('end_date', 'reqd', false);
		}
		else{
			frm.set_value('is_service', false);
			frm.set_df_property('start_date', 'reqd', false);
			frm.set_df_property('end_date', 'reqd', false);
			frm.set_df_property('item_brand', 'reqd', true);
			frm.set_df_property('item_model', 'reqd', true);
			frm.set_df_property('item_material', 'reqd', true);
			frm.set_df_property('item_area_of_use', 'reqd', true);
			frm.set_df_property('item_color', 'reqd', true);
			frm.set_df_property('item_uom', 'reqd', true);
		}
		//Project and designation requirements
		if(frm.doc.subitem_group == 'Uniform'){
			frm.set_df_property('one_fm_project', 'reqd', true);
			frm.set_df_property('one_fm_designation', 'reqd', true);
			frm.set_df_property('item_gender', 'reqd', true);
			frm.set_df_property('item_size', 'reqd', true);
			frm.set_df_property('one_fm_project', 'hidden', 0);
			frm.set_df_property('one_fm_designation', 'hidden', 0);
		}
		else{
			frm.set_df_property('one_fm_project', 'reqd', false);
			frm.set_df_property('one_fm_designation', 'reqd', false);
			frm.set_df_property('item_gender', 'reqd', false);
			frm.set_df_property('item_size', 'reqd', false);
			frm.set_df_property('one_fm_project', 'hidden', 1);
			frm.set_df_property('one_fm_designation', 'hidden', 1);
		}
		//Supplier requirements block
		if(frm.doc.subitem_group == 'Uniform' || frm.doc.subitem_group == 'Bedding'){
			frm.set_df_property('item_supplier', 'reqd', true);
		}
		else{
			frm.set_df_property('item_supplier', 'reqd', false);
		}
		//equipment block
		if(frm.doc.subitem_group == 'Equipment'){
			frm.set_df_property('item_color', 'reqd', false);
		}
		else{
			frm.set_df_property('item_color', 'reqd', true);
		}
		//intangible block
		if(frm.doc.subitem_group == 'Intangible'){
			frm.set_df_property('item_material', 'hidden', 1);
			frm.set_df_property('item_color', 'hidden', 1);
			frm.set_df_property('item_packaging', 'hidden', 1);
			frm.set_df_property('item_brand', 'reqd', false);
			frm.set_df_property('item_model', 'reqd', false);
			frm.set_df_property('item_area_of_use', 'reqd', false);
		}
		else{
			frm.set_df_property('item_material', 'hidden', 0);
			frm.set_df_property('item_color', 'hidden', 0);
			frm.set_df_property('item_packaging', 'hidden', 0);
			frm.set_df_property('item_brand', 'reqd', true);
			frm.set_df_property('item_model', 'reqd', true);
			frm.set_df_property('item_area_of_use', 'reqd', true);
		}
		//Description table block
		
	},
	item_group: function(frm) {
		set_item_field_property(frm);
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
		if(frm.doc.item_group == "Electronics Spare parts" || frm.doc.item_group == "Equipment Spare parts" || frm.doc.item_group == "Vehicles Spare parts" || frm.doc.item_group == "Furniture Spare parts"){
			frm.set_value('is_spare_part', true);
			frm.set_df_property('item_link', 'reqd', true);
		}
		else{
			frm.set_value('is_spare_part', false);
			frm.set_df_property('item_link', 'reqd', false);
		}
		if(frm.doc.item_group == "Electronics Spare parts" || frm.doc.item_group == "Electronics Accessories"){
			frm.set_df_property('item_color', 'reqd', false);
		}
		else{
			frm.set_df_property('item_color', 'reqd', true);
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

var set_item_field_property = function(frm) {
	frm.set_df_property('item_link', 'reqd', false);
}

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
