// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

window.doc={{ doc.as_json() }};

$(document).ready(function() {
	new rfq1();
	doc.supplier = "{{ doc.supplier }}"
	doc.currency = "{{ doc.currency }}"
	doc.number_format = "{{ doc.number_format }}"
	doc.buying_price_list = "{{ doc.buying_price_list }}"
	$('#qtn-attachment-file').on('change', ':file', function() {
		var $input = $(this);
		var file_input = $input.get(0);
		if (file_input.files[0].size > 5242880) {
			alert('max upload size is 5 Mega Byte');
		}
		if(file_input.files.length) {
			file_input.filedata = { "files_data" : [] };
		}
		window.file_reading = true;
		//this will handle multi files input
		$.each(file_input.files, function(key, value) {
			setupReader(value, file_input);
		});
		window.file_reading = false;
	});
});

function setupReader(file, input) {
	let name = file.name;
	var reader = new FileReader();
	reader.onload = function(e) {
	  input.filedata.files_data.push({
	    "__file_attachment": 1,
	    "filename": file.name,
	    "dataurl": reader.result
	  })
	}
	reader.readAsDataURL(file);
}

rfq1 = Class.extend({
	init: function(){
		this.onfocus_select_all();
		this.change_qty();
		this.change_rate();
		this.terms();
		this.submit_rfq1();
		this.navigate_quotations();
	},

	onfocus_select_all: function(){
		$("input").click(function(){
			$(this).select();
		})
	},

	change_qty: function(){
		var me = this;
		$('.rfq-items').on("change", ".rfq-qty", function(){
			me.idx = parseFloat($(this).attr('data-idx'));
			me.qty = parseFloat($(this).val()) || 0;
			me.rate = parseFloat($(repl('.rfq-rate[data-idx=%(idx)s]',{'idx': me.idx})).val());
			me.update_qty_rate();
			$(this).val(format_number(me.qty, doc.number_format, 2));
		})
	},

	change_rate: function(){
		var me = this;
		$(".rfq-items").on("change", ".rfq-rate", function(){
			me.idx = parseFloat($(this).attr('data-idx'));
			me.rate = parseFloat($(this).val()) || 0;
			me.qty = parseFloat($(repl('.rfq-qty[data-idx=%(idx)s]',{'idx': me.idx})).val());
			me.update_qty_rate();
			$(this).val(format_number(me.rate, doc.number_format, 2));
		})
	},

	terms: function(){
		$(".terms").on("change", ".terms-feedback", function(){
			doc.terms = $(this).val();
		})
	},

	update_qty_rate: function(){
		var me = this;
		doc.grand_total = 0.0;
		$.each(doc.items, function(idx, data){
			if(data.idx == me.idx){
				data.qty = me.qty;
				data.rate = me.rate;
				data.amount = (me.rate * me.qty) || 0.0;
				$(repl('.rfq-amount[data-idx=%(idx)s]',{'idx': me.idx})).text(format_number(data.amount, doc.number_format, 2));
			}

			doc.grand_total += flt(data.amount);
			$('.tax-grand-total').text(format_number(doc.grand_total, doc.number_format, 2));
		})
	},

	submit_rfq1: function(){
		$('.btn-sm').click(function(){
			var file_data = {};
			$("[type='file']").each(function(i){
	      file_data[$(this).attr("id")] = $('#'+$(this).attr("id")).prop('filedata');
	    });
			console.log(file_data);
			frappe.freeze();
			frappe.call({
				type: "POST",
				method: "one_fm.one_fm.doctype.request_for_supplier_quotation.request_for_supplier_quotation.create_supplier_quotation",
				args: {
					doc: doc,
					files: file_data
				},
				btn: this,
				callback: function(r){
					frappe.unfreeze();
					if(r.message){
						$('.btn-sm').hide()
						// window.location.href = "/supplier-quotations/" + encodeURIComponent(r.message);
						window.location.href = "/rfq1";
					}
				}
			})
		})
	},

	navigate_quotations: function() {
		$('.quotations').click(function(){
			name = $(this).attr('idx')
			window.location.href = "/quotations/" + encodeURIComponent(name);
		})
	}
})
