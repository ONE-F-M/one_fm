// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Leasing Contract', {
	refresh: function(frm) {

	},
	create_vehicle: function(frm) {
		create_vehicle_dialoge(frm);
	}
});

var create_vehicle_dialoge = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Create New Vehicle',
		fields: [
			{fieldtype: "Link", label: "Vehicle Detail", fieldname: "vehicle_detail", reqd: 1, options:"Vehicle Leasing Contract Item"},
			{fieldtype: "Select", label: "Purpose of Use", fieldname: "purpose_of_use", reqd: 1, options:"Personal\nGeneral"},
			{fieldtype: "Data", label: "License Plate", fieldname: "license_plate", reqd: 1},
			{fieldtype: "Float", label: "Odometer Value (Last)", fieldname: "last_odometer", reqd: 1},
			{fieldtype: "Select", label: "Fuel Type", fieldname: "fuel_type", options:"Petrol\nDiesel\nNatural Gas\nElectric", reqd: 1},
			{fieldtype: "Column Break"},
			{fieldtype: "Float", label: "Fuel Capacity", fieldname: "fuel_capcity"},
			{fieldtype: "Link", label: "Fuel UOM", fieldname: "uom", options: "UOM", reqd: 1},
			{fieldtype: "Float", label: "Milage", fieldname: "milage"},
			{fieldtype: "Section Break"},
			{fieldtype: "Data", label: "Chassis No", fieldname: "chassis_no"},
			{fieldtype: "Date", label: 'Acquisition Date', fieldname: 'acquisition_date'},
			{fieldtype: "Date", label: 'Registry Expiration Date', fieldname: 'one_fm_registry_expiration_date'},
			{fieldtype: "Column Break"},
			{fieldtype: "Data", label: "Color", fieldname: "color"},
			{fieldtype: "Int", label: "Wheels", fieldname: "wheels"},
			{fieldtype: "Int", label: "Doors", fieldname: "doors"}
		],
		primary_action_label: __("Create"),
		primary_action : function(){
			var args = {
				vd: dialog.get_value('vehicle_detail'),
				one_fm_purpose_of_use: dialog.get_value('purpose_of_use'),
				license_plate: dialog.get_value('license_plate'),
				one_fm_fuel_capcity: dialog.get_value('fuel_capcity') || '',
				one_fm_milage: dialog.get_value('milage') || '',
				last_odometer: dialog.get_value('last_odometer'),
				fuel_type: dialog.get_value('fuel_type'),
				uom: dialog.get_value('uom'),
				chassis_no: dialog.get_value('chassis_no'),
				acquisition_date: dialog.get_value('acquisition_date'),
				one_fm_registry_expiration_date: dialog.get_value('one_fm_registry_expiration_date'),
				color: dialog.get_value('color'),
				wheels: dialog.get_value('wheels'),
				doors: dialog.get_value('doors')
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
