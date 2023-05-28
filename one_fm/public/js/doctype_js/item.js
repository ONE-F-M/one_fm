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
					['Item Type', 'item_group', '=', cur_frm.doc.item_group]
				]
			};
		});
		frm.set_query("item_model", function() {
			return {
				filters: [
					['Item Model', 'item_brand', '=', cur_frm.doc.brand]
				]
			};
		});
		var fields = ["linked_items"];
		for ( var i=0; i< fields.length; i++ ){
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
	is_stock_item: function(frm) {
		if(frm.doc.is_stock_item){
			if(frm.doc.workflow_state != 'Approved'){
				frm.set_value('disabled', true);
			}
		}
		else if(frm.is_new()){
			frm.set_value('disabled', false);
		}
	},
	validate: function(frm){
		frm.set_value("item_barcode", cur_frm.doc.item_code)
		// var final_description = ""
		// if(frm.doc.one_fm_project){
		// 	final_description+=frm.doc.one_fm_project
		// }
		// if(frm.doc.one_fm_designation){
		// 	final_description+=(final_description?' - ':'')+frm.doc.one_fm_designation
		// }
		// if(frm.doc.item_type){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_type
		// }
		// if(frm.doc.brand){
		// 	final_description+=(final_description?' - ':'')+frm.doc.brand
		// }
		// if(frm.doc.item_model){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_model
		// }
		// if(frm.doc.item_material){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_material
		// }
		// if(frm.doc.item_area_of_use){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_area_of_use
		// }
		// if(frm.doc.item_color){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_color
		// }
		// if(frm.doc.item_size){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_size
		// }
		// if(frm.doc.item_gender){
		// 	final_description+=(final_description?' - ':'')+frm.doc.item_gender
		// }
		// if(frm.doc.origin){
		// 	final_description+=(final_description?' - ':'')+frm.doc.origin
		// }
		// if(frm.doc.supplier_items){
		// 	frm.doc.supplier_items.forEach((item, i) => {
		// 		final_description+=(final_description?' - ':'')+item.supplier
		// 	});
		// }
		// if(frm.doc.other_description){
		// 	final_description+=(final_description?' - ':'')+frm.doc.other_description
		// }
		// frm.set_value("description", final_description);
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
		if(frm.doc.subitem_group == 'Equipment'){
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_area_of_use', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Fixture'){
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_df_property('item_area_of_use', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Vehicle'){
			// frm.set_df_property('item_material', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_area_of_use', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Intangible'){
			// frm.set_df_property('item_material', 'hidden', 1);
			// frm.set_df_property('item_color', 'hidden', 1);
			// frm.set_df_property('item_material', 'reqd', false);
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_df_property('item_packaging', 'hidden', 1);
			// frm.set_df_property('brand', 'reqd', false);
			// frm.set_df_property('item_model', 'reqd', false);
			// frm.set_df_property('item_area_of_use', 'reqd', false);
			//
			// frm.set_df_property('item_uom', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
		}
		else if(frm.doc.subitem_group == 'Service'){
			// frm.set_value('is_service', true);
			// frm.set_df_property('start_date', 'reqd', false);
			// frm.set_df_property('end_date', 'reqd', false);
			// frm.set_df_property('brand', 'reqd', false);
			// frm.set_df_property('item_model', 'reqd', false);
			// frm.set_df_property('item_material', 'reqd', false);
			// frm.set_df_property('item_area_of_use', 'reqd', false);
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_df_property('item_uom', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
		}
		else if(frm.doc.subitem_group == 'Consumables'){
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Tools'){
			// frm.set_df_property('item_color', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Uniform'){
			// frm.set_value('is_service', true);
			// frm.set_value('have_uniform_type_and_description', true);
			// frm.set_df_property('start_date', 'reqd', false);
			// frm.set_df_property('end_date', 'reqd', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
			// frm.set_df_property('item_area_of_use', 'reqd', false);
			// frm.set_df_property('item_color', 'reqd', true);
			// frm.set_df_property('supplier_items', 'reqd', true);
		}
		else if(frm.doc.subitem_group == 'Bedding'){
			// frm.set_value('is_service', true);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('start_date', 'reqd', false);
			// frm.set_df_property('end_date', 'reqd', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', false);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_area_of_use', 'reqd', false);
			// frm.set_df_property('item_color', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
			// frm.set_df_property('item_uom', 'reqd', true);
			// frm.set_df_property('supplier_items', 'reqd', true);
		}
		else{
			// frm.set_value('is_service', false);
			// frm.set_df_property('start_date', 'reqd', false);
			// frm.set_value('have_uniform_type_and_description', false);
			// frm.set_df_property('end_date', 'reqd', false);
			// frm.set_df_property('brand', 'reqd', true);
			// frm.set_df_property('item_model', 'reqd', true);
			// frm.set_df_property('item_material', 'reqd', true);
			// frm.set_df_property('item_area_of_use', 'reqd', true);
			// frm.set_df_property('item_color', 'reqd', true);

		}
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
			frm.set_df_property('linked_items', 'reqd', true);
		}
		else{
			frm.set_value('is_spare_part', false);
			frm.set_df_property('linked_items', 'reqd', false);
		}
		if(frm.doc.item_group == "Electronics Spare parts" || frm.doc.item_group == "Electronics Accessories" || frm.doc.item_group == "Vehicle Spare parts" || frm.doc.item_group == "Vehicle Accessories"){
			frm.set_df_property('item_color', 'reqd', false);
		}


		// if(frm.doc.item_group){
		// 	frappe.call({
		// 		method: 'frappe.client.get',
		// 		args: {
		// 			doctype: 'Item Group',
		// 			filters: {'name': frm.doc.item_group}
		// 		},
		// 		callback: function(ret) {
		// 			frm.set_value('have_uniform_type_and_description', false);
		// 			frm.clear_table('item_descriptions');
		// 			if(ret && ret.message){
		// 				if(ret.message.is_fixed_asset){
		// 					frm.set_value('is_fixed_asset', ret.message.is_fixed_asset);
		// 					frm.set_value('asset_category', ret.message.asset_category);
		// 				}
		// 			  if(ret.message.one_fm_item_group_descriptions){
		// 			    ret.message.one_fm_item_group_descriptions.forEach((item, i) => {
		// 						if(item.description_attribute == "Uniform Type" || item.description_attribute == "Uniform Type Description"){
		// 							frm.set_value('have_uniform_type_and_description', true);
		// 						}
		// 						else{
		// 							let desc = frappe.model.add_child(frm.doc, 'Item Description', 'item_descriptions');
		// 				      frappe.model.set_value(desc.doctype, desc.name, 'description_attribute', item.description_attribute);
		// 						}
		// 			    });
		// 			  }
		// 			}
		// 			frm.refresh_field('item_descriptions');
		// 		}
		// 	});
		// }
		// else{
		// 	frm.set_value('have_uniform_type_and_description', false);
		// 	frm.clear_table('item_descriptions');
		// 	frm.refresh_field('item_descriptions');
		// }
	},
	item_id: function(frm) {
		if(cur_frm.doc.item_id){
			get_item_code(frm);
		}
	},
	end_date: function(frm) {
		if(frm.doc.start_date>frm.doc.end_date){
			frappe.throw(__('Start Date cannot be set at a date after End Date'))
		}
	}
})

var set_item_field_property = function(frm) {
	frm.set_df_property('linked_items', 'reqd', false);
}

function get_item_code(frm){
	frm.set_value('item_code','')
	frappe.call({
		method: "one_fm.utils.get_item_code",
		args: {
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
