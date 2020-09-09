// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Book Bed', {
	refresh: function(frm) {
		set_filter_for_bed(frm);
	},
	check_availability: function(frm) {
		check_bed_availability(frm);
	},
	accommodation: function(frm) {
		set_filter_for_bed(frm);
	},
	bed_type: function(frm) {
		set_filter_for_bed(frm);
	},
	bed_space_type: function(frm) {
		set_filter_for_bed(frm);
	},
	gender: function(frm) {
		set_filter_for_bed(frm);
	},
	get_nearest_accommodations: function(frm) {
		get_accommodations(frm);
	},
	passport_number: function(frm) {
		set_employee_details(frm)
	}
});

var set_employee_details = function(frm) {
	frappe.call({
		method: 'get_employee_details',
		doc: frm.doc,
		callback: function(r) {
			frm.refresh_fields();
		},
		freeze: true,
		freeze_message: __("Fetching Employee Data ....")
	})
};

var get_accommodations = function(frm) {
	frm.clear_table('nearest_accommodations');
	let filters = get_accommodation_filters(frm);
	frappe.call({
		method: 'one_fm.accommodation.doctype.book_bed.book_bed.get_nearest_accommodation',
		args: {'filters': filters, 'location': frm.doc.location},
		callback: function(r) {
			if(r && r.message && r.message.length > 0){
				let accommodations = r.message;
				accommodations.forEach((accommodation, i) => {
					var nearest_accommodation = frm.add_child('nearest_accommodations');
					nearest_accommodation.accommodation = accommodation.name;
					nearest_accommodation.accommodation_name = accommodation.accommodation;
					nearest_accommodation.governorate = accommodation.accommodation_governorate;
					nearest_accommodation.area = accommodation.accommodation_area;
					nearest_accommodation.vacant_bed = accommodation.vacant_bed
				});
			}
			else{
				frappe.msgprint(__("No Accommodation Found.!!"))
			}
			set_filter_for_accommodation(frm);
			frm.refresh_fields();
		}
	});
};

var set_filter_for_bed = function(frm) {
	if(frm.doc.available_beds){
		let bed_list = [];
		frm.doc.available_beds.forEach((bed, i) => {
			bed_list[i] = bed.bed;
		});
		frm.set_query('bed', function () {
			return {
				filters: {
					'name': ['in', bed_list]
				}
			};
		});
	}
	else{
		let filters = get_bed_filters(frm);
		frm.set_query('bed', function () {
			return {
				filters: filters
			};
		});
	}
};

var set_filter_for_accommodation = function(frm) {
	if(frm.doc.nearest_accommodations){
		let accommodation_list = [];
		frm.doc.nearest_accommodations.forEach((accommodation, i) => {
			if(accommodation.vacant_bed != 'No Vacant Bed'){
				accommodation_list[i] = accommodation.accommodation;
			}
		});
		frm.set_query('accommodation', function () {
			return {
				filters: {
					'name': ['in', accommodation_list]
				}
			};
		});
	}
	else{
		let filters = get_accommodation_filters(frm);
		frm.set_query('accommodation', function () {
			return {
				filters: filters
			};
		});
	}
};

var check_bed_availability = function(frm) {
	frm.clear_table('available_beds');
	let filters = get_bed_filters(frm);
	frappe.call({
		method: 'one_fm.accommodation.doctype.book_bed.book_bed.get_accommodation_bed_space',
		args: {'filters': filters},
		callback: function(r) {
			if(r && r.message && r.message.length > 0){
				let beds = r.message;
				beds.forEach((bed, i) => {
					var available_bed = frm.add_child('available_beds');
					available_bed.bed = bed.name;
					available_bed.bed_type = bed.bed_type;
					available_bed.gender = bed.gender;
					available_bed.accommodation = bed.accommodation;
					available_bed.area = bed.area;
					available_bed.location = bed.location;
					available_bed.governorate = bed.governorate;
				});
			}
			else{
				frappe.msgprint(__("No Vacant Bed Available.!!"))
			}
			set_filter_for_bed(frm);
			frm.refresh_fields();
		}
	});
};

var get_bed_filters = function(frm) {
	var filters = {};
	filters['status'] = 'Vacant';
	filters['disabled'] = false;
	if(frm.doc.accommodation){
		filters['accommodation'] = frm.doc.accommodation;
	}
	if(frm.doc.bed_type){
		filters['bed_type'] = frm.doc.bed_type;
	}
	if(frm.doc.gender){
		filters['gender'] = frm.doc.gender;
	}
	if(frm.doc.bed_space_type){
		filters['bed_space_type'] = frm.doc.bed_space_type;
	}
	return filters
};

var get_accommodation_filters = function(frm) {
	var filters = {};
	// filters['docstatus'] = 1;
	if(frm.doc.governorate){
		filters['accommodation_governorate'] = frm.doc.governorate;
	}
	if(frm.doc.area){
		filters['accommodation_area'] = frm.doc.area;
	}
	return filters
};
