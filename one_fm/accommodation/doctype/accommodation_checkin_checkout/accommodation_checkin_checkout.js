// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Checkin Checkout', {
	refresh: function(frm) {
		set_filters(frm);
	},
	booking_reference: function(frm) {
		set_checkin_details(frm);
	},
	employee: function(frm) {
		set_checkin_details(frm);
	},
	print_asset_receiving_declaration: function(frm) {
		frm.meta.default_print_format = "Asset Receiving Declaration";
		frm.print_doc();
	},
	print_accommodation_policy: function(frm) {
		frm.meta.default_print_format = "Accommodation Policy";
		frm.print_doc();
	},
	checkin_reference: function(frm) {
		set_checkin_details(frm);
	},
	type: function(frm) {
		set_required(frm);
	}
});

var set_required = function(frm) {
	if(frm.doc.type == 'OUT'){
		frm.set_df_property('checkin_reference', 'reqd', true);
		frm.set_df_property('reason_for_checkout', 'reqd', true);
	}
	else{
		frm.set_df_property('checkin_reference', 'reqd', false);
		frm.set_df_property('reason_for_checkout', 'reqd', false);
	}
};

var set_checkin_details = function(frm) {
	frappe.call({
		method: 'get_checkin_details_from_booking',
		doc: frm.doc,
		callback: function(r) {
			frm.refresh_fields();
		}
	});
};

var set_filters = function(frm) {
	frm.set_query('booking_reference', function () {
		return {
			filters: {
				'booking_status': ['in', ['Permanent Booking']]
			}
		};
	});

	frm.set_query('checkin_reference', function () {
		var filters = {};
		filters['type'] = 'IN'
		if(frm.doc.employee){
			filters['employee'] = frm.doc.employee
		}
		return {
			filters: filters
		};
	});

	frm.set_query("floor", function() {
		return {
			query: "one_fm.accommodation.doctype.accommodation_space.accommodation_space.filter_floor",
			filters: {'accommodation': frm.doc.accommodation}
		}
	});

	frm.set_query('accommodation_unit', function () {
		return {
			filters: {
				'accommodation': frm.doc.accommodation,
				'floor_name': frm.doc.floor
			}
		};
	});

	frm.set_query('bed', function () {
		return {
			filters: {
				'accommodation': frm.doc.accommodation,
				'accommodation_unit': frm.doc.accommodation_unit
			}
		};
	});
};
