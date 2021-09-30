// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Checkin Checkout', {
	refresh: function(frm) {
		set_filters(frm);
		set_date(frm);
		set_field_properties(frm);
		if(!frm.is_new() && !frm.is_dirty() && frm.doc.type == 'IN' && !frm.doc.checked_out){
			frm.add_custom_button(__('Transfer Accommodation'), function() {
				transfer_accommodation(frm);
			});
		}
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

var transfer_accommodation = function(frm) {
	if(frm.is_dirty()){
		frappe.throw(__('Please Save the Document and Continue .!'))
	}
	else{
		transfer_accommodation_dialoge(frm);
	}
};

var transfer_accommodation_action = function(frm, bed, transfer_datetime, reason_for_transfer) {
	frappe.call({
		doc: frm.doc,
		method: 'transfer_accommodation',
		args: {bed: bed, transfer_datetime: transfer_datetime, reason_for_transfer: reason_for_transfer},
		callback: function(r) {
			if(!r.exc && r.message){
				frappe.set_route('Form', frm.doc.doctype, r.message);
			}
		},
		freeze: true,
		freeze_message: __('Transfer In Progress ...!')
	});
}

var transfer_accommodation_dialoge = function(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Transfer Accommodation',
		fields: [
			{fieldtype: "Link", label: "Accommodation", fieldname: "accommodation", read_only: 1, options: "Accommodation"},
			{fieldtype: "Link", label: "Floor", fieldname: "floor", reqd: 1, options: "Floor",
				get_query: function(){
					return {
						query: "one_fm.accommodation.doctype.accommodation_space.accommodation_space.filter_floor",
						filters: {'accommodation': dialog.get_value('accommodation')}
					}
				}
			},
			{fieldtype: "Link", label: "Unit", fieldname: "unit", reqd: 1, options: "Accommodation Unit",
				get_query: function(){
					return {
						filters: {
							'accommodation': dialog.get_value('accommodation'),
							'floor_name': dialog.get_value('floor')
						}
					}
				}
			},
			{fieldtype: "Link", label: "Space", fieldname: "space", reqd: 1, options: "Accommodation Space",
				get_query: function(){
					return {
						filters: {
							'accommodation': dialog.get_value('accommodation'),
							'accommodation_unit': dialog.get_value('unit'),
							'bed_space_available': 1
						}
					}
				}
			},
			{fieldtype: "Link", label: "Bed", fieldname: "bed", options:"Bed", reqd: 1,
				get_query: function(){
					return {
						filters: {
							'accommodation': dialog.get_value('accommodation'),
							'accommodation_unit': dialog.get_value('unit'),
							'accommodation_space': dialog.get_value('space'),
							'status': 'Vacant'
						}
					}
				}
			},
			{fieldtype: "Column Break"},
			{fieldtype: "Datetime", label: "Transfer Date Time", fieldname: "transfer_datetime", options:"Today", reqd: 1},
			{fieldtype: "Small Text", label: "Reason for Transfer", fieldname: "reason_for_transfer", reqd: 1}
		],
		primary_action_label: __("Transfer"),
		primary_action : function(){
			if(dialog.get_value('bed')){
				transfer_accommodation_action(frm, dialog.get_value('bed'), dialog.get_value('transfer_datetime'), dialog.get_value('reason_for_transfer'));
				dialog.hide();
			}
			else{
				frappe.throw(__('Please select a Bed to Transfer !!'));
			}
		}
	});
	dialog.set_value('accommodation', frm.doc.accommodation);
	dialog.show();
};

var set_field_properties = function(frm) {
	if(frm.doc.tenant_category == 'Granted Service'){
		frm.set_df_property('employee', 'reqd', true);
		frm.set_df_property('employee', 'hidden', false);
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
				'accommodation_unit': frm.doc.accommodation_unit,
				'status': 'Vacant'
			}
		};
	});
};
