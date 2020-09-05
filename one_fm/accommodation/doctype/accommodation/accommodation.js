// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation', {
	refresh: function(frm) {
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
