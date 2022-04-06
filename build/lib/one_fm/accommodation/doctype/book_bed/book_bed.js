// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Book Bed', {
	refresh: function(frm) {
		set_filter_for_bed(frm);
		manage_book_for(frm);
		frm.fields_dict["available_beds"].grid.frm.$wrapper.find('.grid-footer').hide();
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
	},
	civil_id: function(frm) {
		set_employee_details(frm)
	},
	employee: function(frm) {
		set_employee_details(frm)
	},
	book_for: function(frm) {
		manage_book_for(frm);
	},
	no_of_employees: function(frm) {
		validate_no_of_employees_with_availble_bed(frm);
		set_bulk_bed_book(frm);
	},
	booking_status: function(frm) {
		set_bulk_bed_book(frm);
	},
	local_overseas: function(frm) {
		set_booking_status(frm);
	}
});

var set_booking_status = function(frm) {
	frm.set_value('booking_status', '');
	if(frm.doc.local_overseas){
		if(frm.doc.local_overseas == 'Local'){
			frm.set_value('booking_status', 'Permanent Booking');
		}
		else if(frm.doc.local_overseas == 'Overseas'){
			frm.set_value('booking_status', 'Temporary Booking');
		}
	}
};

var validate_no_of_employees_with_availble_bed = function(frm) {
	if(frm.doc.no_of_employees){
		let available_beds = (frm.doc.available_beds ? frm.doc.available_beds.length : 0);
		if(frm.doc.no_of_employees > available_beds){
			frappe.throw(__('We have only {0} Available Beds.', [available_beds]));
		}
	}
};

var set_bulk_bed_book = function(frm) {
	if(frm.doc.no_of_employees && frm.doc.booking_status && frm.doc.available_beds){
		frm.clear_table('bulk_book_bed');
		frm.doc.available_beds.forEach((item, i) => {
			if(i < frm.doc.no_of_employees){
				var bulk_book_bed = frm.add_child('bulk_book_bed');
				bulk_book_bed.bed = item.bed
				bulk_book_bed.bed_type = item.bed_type
				bulk_book_bed.gender = item.gender
				bulk_book_bed.accommodation = item.accommodation
				bulk_book_bed.governorate = item.governorate
				bulk_book_bed.area = item.area
				bulk_book_bed.location = item.location
				bulk_book_bed.booking_status = frm.doc.booking_status
			}
		});
	}
	frm.refresh_fields();
};

var manage_book_for = function(frm) {
	if(frm.doc.book_for == 'Single'){
		frm.set_df_property('no_of_employees', 'hidden', true);
		frm.set_df_property('no_of_employees', 'reqd', false);
		frm.set_df_property('bed', 'hidden', false);
		frm.set_df_property('bed', 'reqd', true);
	}
	else{
		frm.set_df_property('bed', 'hidden', true);
		frm.set_df_property('bed', 'reqd', false);
		if(frm.doc.book_for == 'Bulk'){
			frm.set_df_property('no_of_employees', 'hidden', false);
			frm.set_df_property('no_of_employees', 'reqd', true);
		}
	}
};

var set_employee_details = function(frm) {
	frappe.call({
		method: 'get_employee_details',
		doc: frm.doc,
		callback: function(r) {
			frm.refresh_fields();
		},
		freeze: true,
		freeze_message: __("Fetching Employee Data ....")
	});
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
					available_bed.accommodation_space = bed.accommodation_space;
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
			frm.fields_dict["available_beds"].grid.frm.$wrapper.on('click', '.grid-row-check', (e) => {
				frm.set_value('bed', '');
				if(frm.fields_dict["available_beds"].grid.frm.$wrapper.find('.grid-body .grid-row-check:checked:first').length){
					frm.fields_dict["available_beds"].grid.frm.$wrapper.find('.grid-remove-rows').hide();
					let selected_bed = frm.get_field('available_beds').grid.get_selected_children();
					if(selected_bed.length > 0){
						frm.set_value('bed', selected_bed[0].bed);
					}
				}
			});
			set_filter_for_bed(frm);
			frm.refresh_fields();
			frm.fields_dict["available_beds"].grid.frm.$wrapper.find('.grid-footer').hide();
		},
		freeze: true,
		freeze_message: __('Checking Availability...')
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
