// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation', {
	onload_post_render: function(frm){
			$('[data-fieldname="map_html"]').append(`<div style='width:100%; height:500px' id='map'></div>`);
			let {latitude, longitude}= frm.doc;
			window.markers = [];
			window.circles = [];
			// JS API is loaded and available
			console.log("Called")
			window.map = new google.maps.Map(document.getElementById('map'), {
					center: {lat: 29.338394, lng: 48.005958},
					zoom: 17
			});
			loadGoogleMap(frm);
	},
	refresh: function(frm) {
		set_qr_code(frm);
		set_contact_html(frm);
		frm.set_query('area', function () {
			return {
				filters: {
					'governorate': frm.doc.governorate
				}
			};
		});
		frm.set_query('authorization_area', function () {
			return {
				filters: {
					'governorate': frm.doc.authorization_governorate
				}
			};
		});
		frm.set_query('accommodation_area', function () {
			return {
				filters: {
					'governorate': frm.doc.accommodation_governorate
				}
			};
		});
	}
});

var set_qr_code = function(frm) {
	let qr_code_html = `{%if doc.name%}
	<div style="display: inline-block;padding: 5%;">
	<div class="qr_code_print" id="qr_code_print">
	<img src="https://barcode.tec-it.com/barcode.ashx?code=MobileQRCode&multiplebarcodes=false&translate-esc=false&data={{url}}&unit=Fit&dpi=150&imagetype=Gif&rotation=0&color=%23000000&bgcolor=%23ffffff&codepage=&qunit=Mm&quiet=2.5&eclevel=H" alt="">
	<p>
		{{qr_details}}
	</p>
	</div>
	<br>
	<input name="qr_b_print" type="button" class="qr_ipt" id="qr_ipt" value=" Print ">
	</div>
	{%endif%}
	<script type="text/javascript">
	$("#qr_ipt").click(function() {
			var divToPrint = document.getElementById("qr_code_print");
			newWin = window.open("");
			newWin.document.write(divToPrint.outerHTML);
			newWin.print();
	});
	</script>`
	var doc = frm.doc;
	var url = frappe.urllib.get_full_url("/api/method/one_fm.accommodation.utils.accommodation_qr_code_live_details?"
		+ "docname=" + encodeURIComponent(doc.name))
	var qr_details = __('{0}<br/>Code: {1}', [doc.accommodation, doc.name])
	var qr_code = frappe.render_template(qr_code_html,{"doc":doc, "qr_details": qr_details, "url": url});
	$(frm.fields_dict["accommodation_qr"].wrapper).html(qr_code);
	refresh_field("accommodation_qr")
};

function loadGoogleMap(frm){
    let lat = 29.338394;
    let lng = 48.005958;
    if(frm.doc.name == '01'){
        lat = 29.269929000;
        lng = 47.966612800;
    }
    else if(frm.doc.name == '02'){
        lat = 29.152381700;
        lng = 48.121065800;
    }
    else if(frm.doc.name == '03'){
        lat = 29.152044100;
        lng = 48.121005200;
    }
    let radius = frm.doc.geofence_radius;
    if(lat !== undefined && lng !== undefined){
        let marker = new google.maps.Marker({
            position: {lat, lng},
            map: map,
            title: frm.doc.location_name
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
};

var set_contact_html = function(frm) {
	var contact_fields = ['owner_contact', 'legal_authorization_contact', 'legal_representative_contact',
		'other_primary_point_of_contact'];
	contact_fields.forEach((contact_field) => {
		let contact_html_field = contact_field+'_html';
		let contact_list_field = contact_field+'_list';

		if(frm.fields_dict[contact_html_field] && contact_list_field in frm.doc.__onload) {
			frappe.dynamic_link = {'doc': frm.doc, 'fieldname': 'name', 'doctype': frm.doc.doctype};

			$(frm.fields_dict[contact_html_field].wrapper)
				.html(frappe.render_template(contact_show_html,
					{'contact_list': frm.doc.__onload[contact_list_field]}))
				.find(".btn-contact").on("click", function() {
					frappe.route_options = {
						"one_fm_doc_contact_field": contact_field
					}
					frappe.new_doc("Contact");
				}
			);
		}
	});
};

var contact_show_html = `
<div class="clearfix"></div>
{% for(var i=0, l=contact_list.length; i<l; i++) { %}
	<div class="address-box">
		<p class="h6">
			{%= contact_list[i].first_name %} {%= contact_list[i].last_name %}
			{% if(contact_list[i].is_primary_contact) { %}
				<span class="text-muted">({%= __("Primary") %})</span>
			{% } %}
			{% if(contact_list[i].designation){ %}
			 <span class="text-muted">&ndash; {%= contact_list[i].designation %}</span>
			{% } %}
			<a href="#Form/Contact/{%= encodeURIComponent(contact_list[i].name) %}"
				class="btn btn-xs btn-default pull-right"
				style="margin-top:-3px; margin-right: -5px;">
				{%= __("Edit") %}</a>
		</p>
		{% if (contact_list[i].phones || contact_list[i].email_ids) { %}
		<p>
			{% if(contact_list[i].phone) { %}
				{%= __("Phone") %}: {%= contact_list[i].phone %}<span class="text-muted"> ({%= __("Primary") %})</span><br>
			{% endif %}
			{% if(contact_list[i].mobile_no) { %}
				{%= __("Mobile No") %}: {%= contact_list[i].mobile_no %}<span class="text-muted"> ({%= __("Primary") %})</span><br>
			{% endif %}
			{% if(contact_list[i].phone_nos) { %}
				{% for(var j=0, k=contact_list[i].phone_nos.length; j<k; j++) { %}
					{%= __("Phone") %}: {%= contact_list[i].phone_nos[j].phone %}<br>
				{% } %}
			{% endif %}
		</p>
		<p>
			{% if(contact_list[i].email_id) { %}
				{%= __("Email") %}: {%= contact_list[i].email_id %}<span class="text-muted"> ({%= __("Primary") %})</span><br>
			{% endif %}
			{% if(contact_list[i].email_ids) { %}
				{% for(var j=0, k=contact_list[i].email_ids.length; j<k; j++) { %}
					{%= __("Email") %}: {%= contact_list[i].email_ids[j].email_id %}<br>
				{% } %}
			{% endif %}
		</p>
		{% endif %}
		<p>
			{% if(contact_list[i].one_fm_civil_id) { %}
				{%= __("CIVIL ID") %}: {%= contact_list[i].one_fm_civil_id %}<br>
			{% endif %}
		</p>
		<p>
		{% if (contact_list[i].address) { %}
			{%= __("Address") %}: {%= contact_list[i].address %}<br>
		{% endif %}
		</p>
	</div>
{% } %}
{% if(!contact_list.length) { %}
<p class="text-muted small">{%= __("No Details added yet.") %}</p>
<p><button class="btn btn-xs btn-default btn-contact">
	{{ __("New Contact") }}</button>
</p>
{% } %}
`;
