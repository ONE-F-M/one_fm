// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Space', {
	accommodation_space_type: function(frm) {
		is_bed_space_available_for_space_type(frm);
	},
	length: function(frm) {
		calculate_area_and_volume(frm);
	},
	width: function(frm) {
		calculate_area_and_volume(frm);
	},
	height: function(frm) {
		calculate_area_and_volume(frm);
	},
	refresh: function(frm){
		set_qr_code(frm);
		set_filters(frm);
	},
	accommodation_unit: function(frm) {
		set_space_type_filter(frm);
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
	var qr_details = __('{0}, {1}<br/>{2} Floor, Unit: {3}<br/>{4}<br/>Code: {5}', [doc.accommodation_name,
		doc.type, doc.floor_name, doc.accommodation_unit, doc.accommodation_space_type, doc.name])
	var qr_code = frappe.render_template(qr_code_html,{"doc":doc, "qr_details": qr_details, "url": url});
	$(frm.fields_dict["space_qr"].wrapper).html(qr_code);
	refresh_field("space_qr")
};

var set_space_type_filter = function(frm) {
	if(frm.doc.accommodation_unit){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Accommodation Unit',
				filters: {name: frm.doc.accommodation_unit}
			},
			callback: function(r){
				var space_types = [];
				if(r && r.message && r.message.space_details){
					r.message.space_details.forEach((item, i) => {
						space_types[i] = item.space_type;
					});
				}
				frm.set_query('accommodation_space_type', function () {
					return {
						filters: {
							'name': ['in', space_types]
						}
					};
				});
			}
		});
	}
	else{
		frm.set_query('accommodation_space_type', function () {
			return {
				filters: {
					'name': ['in', []]
				}
			};
		});
	}
};

var set_filters = function(frm) {
	frm.set_query('accommodation_unit', function () {
		return {
			filters: {
				'accommodation': frm.doc.accommodation,
				'floor_name': frm.doc.floor_name
			}
		};
	});
	frm.set_query("floor_name", function() {
		return {
			query: "one_fm.accommodation.doctype.accommodation_space.accommodation_space.filter_floor",
			filters: {'accommodation': frm.doc.accommodation}
		}
	});
};

var calculate_area_and_volume = function(frm) {
	let area = 0;
	let volume = 0;
	if(frm.doc.length && frm.doc.width){
		area = frm.doc.length * frm.doc.width;
		if(frm.doc.height){
			volume = area * frm.doc.height;
		}
	}
	frm.set_value('area', area);
	frm.set_value('volume', volume);
};

var is_bed_space_available_for_space_type = function(frm) {
	if(frm.doc.accommodation_space_type){
		frappe.db.get_value('Accommodation Space Type', frm.doc.accommodation_space_type, 'bed_space_available', function(r) {
			if(r && r.bed_space_available){
				frm.set_value('bed_space_available', true);
			}
			else{
				frm.set_value('bed_space_available', false);
			}
		});
	}
	else{
		frm.set_value('bed_space_available', false);
	}
};
