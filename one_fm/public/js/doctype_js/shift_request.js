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
		console.log("Called")
		const in_map = new google.maps.Map(document.getElementById('in_map'), {
			center: {lat: 29.338394, lng: 48.005958},
			zoom: 17
		});
		const out_map  = new google.maps.Map(document.getElementById('out_map'), {
			center: {lat: 29.338394, lng: 48.005958},
			zoom: 17
		});
		loadGoogleMap(frm, "IN");
		loadGoogleMap(frm, "OUT");


		// Configure the click listener.
		in_map.addListener('click', function(mapsMouseEvent) {
			clearMarkers();
			clearCircles();
			frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'checkin_latitude', mapsMouseEvent.latLng.lat());
			frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'checkin_longitude',mapsMouseEvent.latLng.lng());
		});
		out_map.addListener('click', function(mapsMouseEvent) {
			clearMarkers();
			clearCircles();
			frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'checkout_latitude', mapsMouseEvent.latLng.lat());
			frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'checkout_longitude',mapsMouseEvent.latLng.lng());
		});

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
});

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
					console.log(r.message)
                    frm.set_value("approver",r.message)
					frm.set_value("shift_approver",r.message)
                }
            }
        });
    }
}

function loadGoogleMap(frm, log_type){
	var lat, lng, radius, title;
	if(log_type == "IN"){
		lat = frm.doc.checkin_latitude;
		lng = frm.doc.checkin_longitude;
		radius = frm.doc.checkin_radius;
		title = frm.doc.check_in_site
	}
	else{
		lat = frm.doc.checkout_latitude;
		lng = frm.doc.checkout_longitude;
		radius = frm.doc.checkout_radius;
		title = frm.doc.check_out_site
	}
	
	if(lat !== undefined && lng !== undefined){
		let marker = new google.maps.Marker({
			position: {lat, lng},
			map: map,
			title: title
		});
		marker.setMap(map);
		map.setCenter({lat, lng});
		markers.push(marker);

		if(radius){
			let geofence_circle = new google.maps.Circle({
				strokeColor: '#FF0000',
				strokeOpacity: 0.8,
				strokeWeight: 2,
				fillColor: '#FF0000',
				fillOpacity: 0.35,
				map: map,
				center: {lat, lng},
				radius: radius,
				clickable: false
			});
			circles.push(geofence_circle);
		}
		}
			
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