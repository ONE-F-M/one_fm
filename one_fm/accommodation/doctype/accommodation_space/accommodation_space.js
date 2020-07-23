// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Space', {
	accommodation_space_type: function(frm) {
		is_bed_space_available_for_space_type(frm);
	},
	length: function(frm) {
		calculate_area_and_volume(frm);
	},
	width: function(frm) {
		calculate_area_and_volume(frm);
	},
	height: function(frm) {
		calculate_area_and_volume(frm);
	}
});

var calculate_area_and_volume = function(frm) {
	let area = 0;
	let volume = 0;
	if(frm.doc.length && frm.doc.width){
		area = frm.doc.length * frm.doc.width;
		if(frm.doc.height){
			volume = area * frm.doc.height;
		}
	}
	frm.set_value('area', area);
	frm.set_value('volume', volume);
};

var is_bed_space_available_for_space_type = function(frm) {
	if(frm.doc.accommodation_space_type){
		frappe.db.get_value('Accommodation Space Type', frm.doc.accommodation_space_type, 'bed_space_available', function(r) {
			if(r && r.bed_space_available){
				frm.set_value('bed_space_available', true);
			}
			else{
				frm.set_value('bed_space_available', false);
			}
		});
	}
	else{
		frm.set_value('bed_space_available', false);
	}
};
