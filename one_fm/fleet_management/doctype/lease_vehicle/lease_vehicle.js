// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lease Vehicle', {
	refresh: function(frm) {
		disable_create_vehicle_button(frm);
	},
	create_vehicle: function(frm) {
		create_vehicle_dialoge(frm);
	}
});

var disable_create_vehicle_button = function(frm) {
	console.log(frm.doc.vehicles.length);
	if(frm.doc.quantity == frm.doc.vehicles.length){
		frm.set_df_property('create_vehicle', 'hidden', true);
	}
};

var create_vehicle_dialoge = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Create New Vehicle',
		fields: [
			{fieldtype: "Select", label: "Purpose of Use", fieldname: "purpose_of_use", reqd: 1, options:"Personal\nGeneral"},
			{fieldtype: "Data", label: "License Plate", fieldname: "license_plate", reqd: 1},
			{fieldtype: "Float", label: "Odometer Value (Last)", fieldname: "last_odometer", reqd: 1},
			{fieldtype: "Select", label: "Fuel Type", fieldname: "fuel_type", options:"Petrol\nDiesel\nNatural Gas\nElectric", reqd: 1},
			{fieldtype: "Column Break"},
			{fieldtype: "Float", label: "Fuel Capacity", fieldname: "fuel_capcity"},
			{fieldtype: "Link", label: "Fuel UOM", fieldname: "uom", options: "UOM", reqd: 1},
			{fieldtype: "Float", label: "Milage", fieldname: "milage"}
		],
		primary_action_label: __("Create"),
		primary_action : function(){
			var args = {
				one_fm_purpose_of_use: dialog.get_value('purpose_of_use'),
				license_plate: dialog.get_value('license_plate'),
				one_fm_fuel_capcity: dialog.get_value('fuel_capcity') || '',
				one_fm_milage: dialog.get_value('milage') || '',
				last_odometer: dialog.get_value('last_odometer'),
				fuel_type: dialog.get_value('fuel_type'),
				uom: dialog.get_value('uom')
			}
			frappe.call({
				doc: frm.doc,
				method: "create_vehicle",
				args: args,
				callback: function(data) {
					if(!data.exc){
						frm.reload_doc();
						// refresh_field('vehicles');
					}
				},
				freeze: true,
				freeze_message: "Creating Vehicle ..."
			});
			frm.refresh_fields();
			dialog.hide();
		}
	});
	dialog.show();
	dialog.$wrapper.find('.modal-dialog').css("width", "800px");
};
