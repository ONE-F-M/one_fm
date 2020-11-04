// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Checkin Checkout', {
	refresh: function(frm) {
		set_filters(frm);
		set_date(frm);
		set_field_properties(frm);
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
	},
	tenant_category: function(frm) {
		set_field_properties(frm);
	}
});

var set_field_properties = function(frm) {
	if(frm.doc.tenant_category == 'Permanent Employee'){
		frm.set_df_property('employee', 'reqd', true);
		frm.set_df_property('employee', 'hidden', false);
	}
	else if(frm.doc.tenant_category == 'Temporary Employee'){
		frm.set_df_property('employee', 'reqd', false);
		frm.set_df_property('employee', 'hidden', true);
	}
	else if(frm.doc.tenant_category == 'Rental Service'){
		frm.set_df_property('employee', 'reqd', false);
		frm.set_df_property('employee', 'hidden', true);
	}
	else{
		frm.set_df_property('employee', 'reqd', false);
		frm.set_df_property('employee', 'hidden', true);
	}
};

var set_date = function(frm) {
	if(frm.is_new()){
		frm.set_value('checkin_checkout_date_time', frappe.datetime.now_datetime());
	}
};

var set_required = function(frm) {
	if(frm.doc.type == 'OUT'){
		frm.set_df_property('checkin_reference', 'reqd', true);
		frm.set_df_property('reason_for_checkout', 'reqd', true);
		frm.set_df_property('new_or_current_resident', 'reqd', false);
	}
	else if(frm.doc.type == 'IN'){
		frm.set_df_property('checkin_reference', 'reqd', false);
		frm.set_df_property('reason_for_checkout', 'reqd', false);
		frm.set_df_property('new_or_current_resident', 'reqd', true);
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
		var filters = {'type': 'IN', 'checked_out': false};
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

	frm.set_query('employee', function () {
		return {
			filters: {
				'one_fm_provide_accommodation_by_company': true
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
