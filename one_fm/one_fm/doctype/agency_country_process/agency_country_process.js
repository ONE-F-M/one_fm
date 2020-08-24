// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agency Country Process', {
	refresh: function(frm) {
		if(frm.is_new()){
			frm.toggle_display(['agency_country_process_template'], true);
		}
		else{
			frm.toggle_display(['agency_country_process_template'], false);
		}
		set_agency_address_and_contact(frm);
	},
	agency: function(frm) {
		set_agency_address_and_contact(frm);
	},
	validate: function(frm) {
		find_total_duration(frm);
	},
	agency_country_process_template: function(frm) {
		set_process_details(frm);
	}
});

var set_process_details = function(frm) {
	if(frm.doc.agency_country_process_template){
		frm.doc.agency_process_details = [];
		frappe.model.with_doc("Agency Country Process Template", frm.doc.agency_country_process_template, function() {
			var template= frappe.model.get_doc("Agency Country Process Template", frm.doc.agency_country_process_template)
			$.each(template.agency_process_details, function(index, row){
				var d = frm.add_child("agency_process_details");
				d.process_name = row.process_name;
				d.responsible = row.responsible;
				d.duration_in_days = row.duration_in_days;
				d.attachment_required = row.attachment_required;
				d.notes_required = row.notes_required;
				d.reference_type = row.reference_type;
				d.reference_complete_status_field = row.reference_complete_status_field;
				d.reference_complete_status_value = row.reference_complete_status_value;
				d.expected_date = frappe.datetime.add_days(frm.doc.start_date, row.duration_in_days);
			});
			frm.refresh_field("agency_process_details");
		});
	}
};

var set_agency_address_and_contact = function(frm) {
	if(frm.doc.agency){
		if(frm.is_new()){
			frappe.call({
				doc: frm.doc,
				method: 'load_address_and_contact',
				callback: function(r) {
					set_address_and_contact_html(frm);
				}
			});
		}
		else{
			set_address_and_contact_html(frm);
		}
	}
	else{
		frappe.contacts.clear_address_and_contact(frm);
	}
};

var set_address_and_contact_html = function(frm) {
  frm.toggle_display(['address_html','contact_html'], true);
	var address_list = `<div class="clearfix"></div>
	{% for(var i=0, l=addr_list.length; i<l; i++) { %}
	<div class="address-box">
		<p class="h6">
			{%= i+1 %}. {%= addr_list[i].address_title %}{% if(addr_list[i].address_type!="Other") { %}
			<span class="text-muted">({%= __(addr_list[i].address_type) %})</span>{% } %}
			{% if(addr_list[i].is_primary_address) { %}
			<span class="text-muted">({%= __("Primary") %})</span>{% } %}
			{% if(addr_list[i].is_shipping_address) { %}
			<span class="text-muted">({%= __("Shipping") %})</span>{% } %}
		</p>
		<p>{%= addr_list[i].display %}</p>
	</div>
	{% } %}
	{% if(!addr_list.length) { %}
	<p class="text-muted small">{%= __("No address added yet.") %}</p>
	{% } %}`;

	// render address
	if(frm.fields_dict['address_html'] && "addr_list" in frm.doc.__onload) {
		$(frm.fields_dict['address_html'].wrapper)
			.html(frappe.render_template(address_list, frm.doc.__onload));
	}

	// render contact
	var contact_list = `<div class="clearfix"></div>
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
			{% if (contact_list[i].address) { %}
				{%= __("Address") %}: {%= contact_list[i].address %}<br>
			{% endif %}
			</p>
		</div>
	{% } %}
	{% if(!contact_list.length) { %}
	<p class="text-muted small">{%= __("No contacts added yet.") %}</p>
	{% } %}`;

	if(frm.fields_dict['contact_html'] && "contact_list" in frm.doc.__onload) {
		$(frm.fields_dict['contact_html'].wrapper)
			.html(frappe.render_template(contact_list, frm.doc.__onload));
	}
};

frappe.ui.form.on("Agency Process Details", {
	duration_in_days: function (frm, cdt, cdn) {
    find_total_duration(frm);
	}
});

var find_total_duration = function(frm){
    var total_duration = 0;
    $.each(frm.doc.agency_process_details || [], function (i, d) {
        if(d.duration_in_days){
            total_duration += flt(d.duration_in_days);
        }
    });
    frm.set_value("total_duration", total_duration);
};
