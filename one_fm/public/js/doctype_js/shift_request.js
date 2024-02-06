// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
	onload_post_render: function(frm){
		$('[data-fieldname="checkin_map_html"]').append(`<div style='width:100%; height:500px' id='in_map'></div>`);
		$('[data-fieldname="checkout_map_html"]').append(`<div style='width:100%; height:500px' id='out_map'></div>`);
		let {checkin_latitude, checkin_longitude, checkout_latitude,checkout_longitude }= frm.doc;
		window.markers = [];
		window.circles = [];
		// JS API is loaded and available
		clearMarkers();
		clearCircles();

	},
	onload: function(frm){
		prefillForm(frm);
		set_employee_filters(frm)
		
	},
	refresh: function(frm) {
		
		frm.set_df_property('shift_type', 'hidden', 1);
		frm.set_df_property('company', 'hidden', 1);
		frm.set_df_property('approver', 'hidden', 1);
		frm.set_df_property('assign_day_off', 'hidden', 1);
		set_update_request_btn(frm);
		if((frm.doc.custom_replace_existing_shift)&&(frm.doc.custom_replaced_employee)){
			set_replace_shift_assignment(frm)
		}
	},
	
	employee: function(frm) {
		set_approver(frm)
	},
	custom_purpose:function(frm){
		if (frm.doc.custom_purpose=="Assign Day Off"){
			
			frm.doc.assign_day_off = 1
			frm.refresh_field('assign_day_off')
		}
		else{
			frm.doc.assign_day_off = 0
			frm.refresh_field('assign_day_off')
		}
		
	},
	custom_replaced_employee : function(frm){
		if(frm.doc.custom_purpose == "Replace Employee in Shift"){
			set_replace_shift_assignment(frm)
		}
		
	},
	check_in_site:function(frm){
		loadGoogleMap(frm, "IN");
	},
	check_out_site:function(frm){
		loadGoogleMap(frm, "OUT");
	},
	operations_shift : function(frm) {
		let {operations_shift} = frm.doc;
		if(operations_shift){
			frm.set_query("operations_role", function() {
				return {
					query: "one_fm.api.doc_methods.shift_request.get_operations_role",
					filters: {operations_shift}
				};
			});

		}
	}
});


 let set_replace_shift_assignment = function(frm){
	frm.set_query("custom_shift_assignment", function() {
		return {
			"filters": {
				"shift": frm.doc.operations_shift,
				"operations_role": frm.doc.operations_role,
				"employee":frm.doc.custom_replaced_employee,
				"start_date":frm.doc.from_date,
				'roster_type':frm.doc.roster_type
				
			}
		};
	});
}

function set_update_request_btn(frm) {
	if(frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && !frm.doc.update_request){
		frappe.db.get_value('Employee', frm.doc.employee, 'user_id', function(r) {
			if((frappe.session.user == frm.doc.approver) || (r.user_id && frappe.session.user == r.user_id)){
				frm.add_custom_button(__('Update Request'), function() {
					update_request(frm);
				});
			}
		});
	}
};

function update_request(frm) {
	var dialog = new frappe.ui.Dialog({
		title: 'Update Request',
		fields: [
			{
				fieldtype: "Date", label: "From Date", fieldname: "from_date",
				onchange: function () {
					dialog.set_values({
						'to_date': dialog.get_value('from_date')
					});
				}
			},
			{fieldtype: "Date", label: "To Date", fieldname: "to_date"},
		],
		primary_action_label: __("Update"),
		primary_action : function(){
			frappe.confirm(
				__('Are you sure to proceed?'),
				function(){
					// Yes
					frappe.call({
						method: 'one_fm.api.doc_methods.shift_request.update_request',
						args: {
							shift_request: frm.doc.name,
							from_date: dialog.get_value('from_date'),
							to_date: dialog.get_value('to_date'),
						},
						callback: function(r) {
							if(!r.exc) {
								frm.reload_doc();
							}
						},
						freaze: true,
						freaze_message: __("Update Request ..")
					});
					dialog.hide();
				},
				function(){
					// No
					dialog.hide();
				}
			);
		}
	});
	dialog.show();
};

function set_approver(frm){
    if(frm.doc.employee){
        frappe.call({
            method: 'one_fm.api.doc_methods.shift_request.fetch_approver',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("approver",r.message)
					frm.set_value("shift_approver",r.message)
                }
            }
        });
    }
	if(!frm.doc.employee_name && frm.doc.employee){
		frappe.call({
            method: 'one_fm.api.doc_methods.shift_request.fetch_employee_details',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("operations_shift",r.message.shift)
					frm.set_value("shift",r.message.default_shift)
					frm.set_value("site",r.message.site)
					frm.set_value("employee_name",r.message.employee_name)
					frm.set_value("project",r.message.project)
					frm.set_value("department",r.message.department)
					frm.set_value("company_name",r.message.company)
					frm.set_value("company",r.message.company)

                }
            }
        });
	}
}

function loadGoogleMap(frm, log_type){
	var latitude, longitude, geofence_radius, map, title;
	if(log_type == "IN"){
		latitude = frm.doc.checkin_latitude;
		longitude = frm.doc.checkin_longitude;
		geofence_radius = frm.doc.checkin_radius;
		title = frm.doc.check_in_site
		map = new google.maps.Map(document.getElementById('in_map'), {
			center: {lat: latitude, lng: longitude},
			zoom: 17
		});
	}
	else{
		latitude = frm.doc.checkout_latitude;
		longitude = frm.doc.checkout_longitude;
		geofence_radius = frm.doc.checkout_radius;
		title = frm.doc.check_out_site
		map  = new google.maps.Map(document.getElementById('out_map'), {
			center: {lat: latitude, lng: longitude},
			zoom: 17
		});
	}
	
	
	let locationMarker = new google.maps.Circle({
		map: map,
		animation: google.maps.Animation.DROP,
		fillColor: "red",
		center: {lat: latitude, lng: longitude},
		radius: geofence_radius
	});
	markers.push(locationMarker);
	// this.addYourLocationButton(map, locationMarker);
			
} 

function clearMarkers(){
    for (var i = 0; i < markers.length; i++) {
        markers[i].setMap(null);
      }
}
function clearCircles(){
    for (var i = 0; i < circles.length; i++) {
        circles[i].setMap(null);
      }
}


let set_employee_filters = frm=>{
	frm.set_query("employee", function() {
		return {
			query: "one_fm.api.doc_methods.shift_request.get_employees",
			
		};
	});

}



var prefillForm = frm =>{
	const url = new URL(window.location.href);

	const params = new URLSearchParams(url.search);

	const doc_id = params.get('doc_id');
	const doctype = params.get('doctype'); 

	if (doctype == "Attendance Check"){
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				'doctype': doctype,
				'filters': {'name': doc_id},
				'fieldname': [
					"employee"
				]
			},
			callback: function(r) {
				if (r.message) {
					cur_frm.set_value("employee", r.message.employee)
					
				}
			}
		});
	}
}