// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request for Purchase', {
	refresh: function(frm) {
		set_intro_related_to_status(frm);
		frm.events.make_custom_buttons(frm);
		if(!frm.doc.approver || (frm.doc.approver != frm.doc.__onload.approver)){
			frm.set_value('approver', frm.doc.__onload.approver);
		}
		if(!frm.doc.accepter || (frm.doc.accepter != frm.doc.__onload.accepter)){
			frm.set_value('accepter', frm.doc.__onload.accepter);
		}
	},
	status: function(frm) {
		if(frm.doc.status && frm.doc.status == 'Rejected'){
			frm.set_df_property('reason_for_rejection', 'reqd', true);
		}
		else{
			frm.set_df_property('reason_for_rejection', 'reqd', false);
		}
	},
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1){
			if(frm.doc.status == 'Draft') {
				frm.add_custom_button(__("Request for Quotation"),
					() => frm.events.make_request_for_quotation(frm), __('Create'));

				frm.add_custom_button(__("Compare Quotations"),
					() => frm.events.make_quotation_comparison_sheet(frm));
			}
			if(frm.doc.status == 'Approved'){
				frm.add_custom_button(__("Purchase Order"),
					() => frm.events.make_purchase_order(frm), __('Create'));
			}
		}
		if (frm.doc.docstatus == 1){
			if(frappe.session.user==frm.doc.owner && frm.doc.status == "Draft" && frm.doc.items_to_order && frm.doc.items_to_order.length > 0){
				// Changed from "Send request" while removing authorizations and approvals.
				frm.add_custom_button(__('Confirm Item Details'), () => frm.events.send_request_for_purchase(frm, 'Draft Request')).addClass('btn-primary');
			}
			if("accepter" in frm.doc.__onload && frappe.session.user==frm.doc.__onload.accepter && frm.doc.status == "Draft Request"){
				frm.add_custom_button(__('Accept'), () => frm.events.confirm_accept_approve_request_for_purchase(frm, 'Accepted')).addClass('btn-primary');
				frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_purchase(frm, 'Rejected')).addClass('btn-danger');
			}
			if("approver" in frm.doc.__onload && frappe.session.user==frm.doc.__onload.approver && frm.doc.status == "Accepted"){
				frm.add_custom_button(__('Approve'), () => frm.events.confirm_accept_approve_request_for_purchase(frm, 'Approved')).addClass('btn-primary');
				frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_purchase(frm, 'Rejected')).addClass('btn-danger');
			}
		}
	},
	reject_request_for_purchase: function(frm, status) {
		var d = new frappe.ui.Dialog({
			title : __("Reject Request for Purchase"),
			fields : [{
				fieldtype: "Small Text",
				label: "Reason for Rejection",
				fieldname: "reason_for_rejection",
				reqd : 1
			}],
			primary_action_label: __("Reject"),
			primary_action: function(){
				frm.events.accept_approve_reject_request_for_purchase(frm, status, d.get_value('reason_for_rejection'));
				d.hide();
			},
		});
		d.show();
	},
	//Currently just being used as confirmation(i.e bypassing approvals)
	send_request_for_purchase: function(frm, status) {
		frappe.confirm(
			__('Do You Want to confirm Request for Purchase'),
			function(){
				// Yes
				frappe.call({
					doc: frm.doc,
					method: 'send_request_for_purchase',
					callback(r) {
						if (!r.exc) {
							frm.events.confirm_accept_approve_request_for_purchase(frm, 'Approved').addClass('btn-primary');
						}
					},
					freeze: true,
					freeze_message: "Sending ..!"
				});
			},
			function(){} // No
		);
	},
	confirm_accept_approve_request_for_purchase: function(frm, status) {
		let msg_status = 'Approve';
		if(status != 'Approved'){
			msg_status = status == 'Accepted' ? 'Accept': 'Reject'
		}
		frappe.confirm(
			__('A one time code will be sent to you for verification in order to use your signature for approval. Do You Want to {0} this Request for Purchase?', [msg_status]),
			function(){
				// Yes
				var doctype = frm.doc.doctype
				var document_name = frm.doc.name
				frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				var d = new frappe.ui.Dialog({
					title : __("Approval verification"),
					fields : [
						{
							fieldtype: "Int",
							label: "Enter verification code sent to your email address",
							fieldname: "verification_code",
							reqd: 1,
							onchange: function(){
								let code = d.get_value('verification_code')
								if (!is_valid_verification_code(code)){frappe.throw(__("Invalid verification code."))}
							}
						},
						{
							fieldtype: "Button", 
							label: "Resend code", 
							fieldname: "resend_verification_code"
						},
						{
							fieldtype: "HTML",
							label: "Time remaining",
							fieldname: "timer"
						}
					],
					primary_action_label: __("Submit"),
					primary_action: function(){
						var verification_code = d.get_value('verification_code');
						frappe.xcall('one_fm.utils.verify_verification_code', {doctype, document_name, verification_code})
							.then(res => {
								if (res){
									d.hide()
									frm.events.accept_approve_reject_request_for_purchase(frm, status, false);
								} else{
									frappe.msgprint(__("Incorrect verification code. Please try again."));
								}
							})
					},
				});
				d.fields_dict.resend_verification_code.input.onclick = function() {
					reset_timer();
					frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name})
					.then(res => {
						console.log(res);
					}).catch(e => {
						console.log(e);
					})
				}
				start_timer(60*5, d);
				d.show();
			},
			function(){} // No
		);
	},
	accept_approve_reject_request_for_purchase: function(frm, status, reason_for_rejection) {
		frappe.call({
			doc: frm.doc,
			method: 'accept_approve_reject_request_for_purchase',
			args: {
				status: status,
				accepter: frm.doc.__onload.accepter,
				approver: frm.doc.__onload.approver,
				reason_for_rejection: reason_for_rejection
			},
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
			freeze: true
		});
	},
	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_quotation_comparison_sheet: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_quotation_comparison_sheet",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_purchase_order: function(frm) {
		console.log(frm.doc)
		frappe.call({
			doc: frm.doc,
			method: 'make_purchase_order_for_quotation',
			callback: function(data) {
				if(!data.exc){
					frm.reload_doc();
					frappe.show_alert({
						message: "Purchase Order Created",
						indicator: "green"
					});
				}
			},
			freeze: true,
			freeze_message: "Creating Purchase Order"
		})
	},
	get_requested_items_to_order: function(frm) {
		frm.clear_table('items_to_order');
		frm.doc.items.forEach((item, i) => {
			var items_to_order = frm.add_child('items_to_order');
			items_to_order.item_code = item.item_code
			items_to_order.item_name = item.item_name
			items_to_order.description = item.description
			items_to_order.uom = item.uom
			items_to_order.qty = item.qty
			items_to_order.delivery_date = item.schedule_date
			items_to_order.request_for_material = item.request_for_material
		});
		frm.refresh_fields();
	},
	supplier: function(frm) {
		set_supplier_to_items_to_order(frm);
	}
});

var set_intro_related_to_status = function(frm) {
	if (frm.doc.docstatus == 1){
		if(frm.doc.status == 'Draft') {
			frm.set_intro(__("Create Request for Quotation (Optional)."), 'yellow');
			frm.set_intro(__("Compare Quotations if Quotaiton Available (Optional)."), 'yellow');
			frm.set_intro(__("Fill Items to Order - Check Supplier and Item Code set Correctly."), 'yellow');
			frm.set_intro(__("Requester can use Confirm button once items are filled and updated"), 'yellow');
			frm.set_intro(__("Then you will be able to create a PO from the create dropdown button"), 'yellow');
			// frm.set_intro(__("On Accept notify Approver"), 'yellow');
			// frm.set_intro(__("On Approval, Requester can create PO"), 'yellow');
		}
		if(frm.doc.status == 'Approved'){
			frappe.db.get_value("Purchase Order", {"one_fm_request_for_purchase": frm.doc.name}, "name", function(r) {
				if(!r || !r.name){
					frm.set_intro(__("Requester can create PO"), 'yellow');
				}
			})
		}
	}
	if (frm.doc.docstatus == 1){
		if(frm.doc.status == "Draft" && !frm.doc.items_to_order){
			frm.set_intro(__("Fill Items to Order - Check Supplier and Item Code set Correctly."), 'yellow');
			frm.set_intro(__("Requester Click Confirm Button to confirm"), 'yellow');
			frm.set_intro(__("On Confirmation, Requester can create PO"), 'yellow');
			// frm.set_intro(__("Requester Click Send Request Button to notify Accepter"), 'yellow');
			// frm.set_intro(__("On Accept notify Approver"), 'yellow');
			// frm.set_intro(__("On Approval, Requester can create PO"), 'yellow');
		}
		if(frm.doc.status == "Draft Request"){
			frm.set_intro(__("On Accept notify Approver"), 'yellow');
			frm.set_intro(__("On Approval, Requester can create PO"), 'yellow');
		}
		if(frm.doc.status == "Accepted"){
			frm.set_intro(__("On Approval, Requester can create PO"), 'yellow');
		}
	}
};

var set_supplier_to_items_to_order = function(frm){
	if(frm.doc.items_to_order){
		frm.doc.items_to_order.forEach((item) => {
			frappe.model.set_value(item.doctype, item.name, 'supplier', frm.doc.supplier);
		});
		frm.refresh_field('items_to_order');
	}
};

var timer;
function start_timer(duration, d) {
    timer = duration;
    var minutes, seconds;
    setInterval(function () {
        minutes = parseInt(timer / 60, 10)
        seconds = parseInt(timer % 60, 10);

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        d.set_value('timer', "Verification code expires in: " + minutes + ":" + seconds);

        if (--timer < 0) {
            timer = duration;
        }
    }, 1000);
}

function reset_timer() {
  timer = 60 * 5;
}

function is_valid_verification_code(code){
	const code_expression = /^\d{6}(\s*,\s*\d{6})*$/;
	if (code_expression.test(code))  return true;

	return false;
};