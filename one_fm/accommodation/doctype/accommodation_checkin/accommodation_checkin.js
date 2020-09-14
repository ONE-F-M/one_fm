// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Checkin', {
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
	}
});

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
