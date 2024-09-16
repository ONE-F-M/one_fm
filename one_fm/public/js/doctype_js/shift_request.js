// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
	onload_post_render: function(frm){
		$('[data-fieldname="checkin_map_html"]').empty().append(`<div style='width:100%; height:500px' id='in_map'></div>`);
		$('[data-fieldname="checkout_map_html"]').empty().append(`<div style='width:100%; height:500px' id='out_map'></div>`);
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
		set_update_request_btn(frm);
	},
	employee: function(frm) {
		set_approver(frm)
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
					query: "one_fm.overrides.shift_request.get_operations_role",
					filters: {operations_shift}
				};
			});

		}
	},
	purpose: function(frm){
		update_shift_role(frm);

	},
	replaced_employee: function (frm){
		update_shift_role(frm);

	}
});

function set_update_request_btn(frm) {
	if(frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && !frm.doc.update_request){
		frappe.db.get_value('Employee', frm.doc.employee, 'user_id', function(r) {
			approvers = frm.doc.custom_shift_approvers.map(approver => approver.user);
			if(approvers.includes(frappe.session.user) || (r.user_id && frappe.session.user == r.user_id)){
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
						method: 'one_fm.overrides.shift_request.update_request',
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
            method: 'one_fm.overrides.shift_request.fetch_approver',
            args:{
                'doc':frm.doc
            },
            callback: function(r) {
                if(r.message){
                    frm.set_value("approver",r.message[0])
					frm.set_value("shift_approver",r.message[0])
					frm.clear_table("custom_shift_approvers");
					for(let i=0; i<r.message.length; i++){
						frm.add_child("custom_shift_approvers", {"user": r.message[i]});
					}
					frm.refresh_field("custom_shift_approvers");
                }
            }
        });
    }
	if(!frm.doc.employee_name && frm.doc.employee){
		frappe.call({
            method: 'one_fm.overrides.shift_request.fetch_employee_details',
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
			query: "one_fm.overrides.shift_request.get_employees",
			
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

const update_shift_role = (frm) => {
	if (frm.doc.purpose == "Replace Existing Assignment" && frm.doc.replaced_employee){
		frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Shift Assignment",
					fields: ["operations_role", "shift"],
					order_by: "modified desc",
					filters: {
						"employee": frm.doc.replaced_employee
					},
					limit_page_length: 1
				},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					var last_doc = r.message[0];
					frm.set_value({
						operations_role: last_doc.operations_role,
						operations_shift: last_doc.shift
					})

				}
    }
			}

		)
	}
};