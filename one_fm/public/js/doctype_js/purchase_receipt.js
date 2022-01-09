this.frm.dashboard.add_transactions([
    {
        'items': [
            'Customer Asset'
            
        ],
        'label': 'Related'
    },

]);

frappe.ui.form.on('Purchase Receipt', {
	status: function(frm){
		if(frm.doc.status == "Completed"){
			confirm_accept_approve_purchase_receipt(frm);
		}
	}
});
var confirm_accept_approve_purchase_receipt = function(frm) {
	frappe.confirm(
		__('A one time code will be sent to you for verification in order to use your signature for approval. Do You Want to {0} this Request for Material?', [msg_status]),
		function(){
			// Yes
			var doctype = frm.doc.doctype
			var document_name = frm.doc.name
			var d = new Date();
			var current_datetime_string = d.getUTCFullYear() +"/"+ (d.getUTCMonth()+1) +"/"+ d.getUTCDate() + " " + d.getUTCHours() + ":" + d.getUTCMinutes() + ":" + d.getUTCSeconds();
			frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
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
				],
				primary_action_label: __("Submit"),
				primary_action: function(){
					var verification_code = d.get_value('verification_code');
					frappe.xcall('one_fm.utils.verify_verification_code', {doctype, document_name, verification_code})
						.then(res => {
							if (res){
								d.hide()
								accept_approve_purchase_order(frm);
							} else{
								frappe.msgprint(__("Incorrect verification code. Please try again."));
							}
						})
				},
			});
			d.fields_dict.resend_verification_code.input.onclick = function() {
				frappe.xcall('one_fm.utils.send_verification_code', {doctype, document_name, current_datetime_string})
				.then(res => {
					console.log(res);
				}).catch(e => {
					console.log(e);
				})
			}
			d.show();
		},
		function(){} // No
	);
};
var accept_approve_purchase_order = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'one_fm.purchase.utils.accept_approve_purchase_receipt',
		args: {doc: frm.doc},
		callback(r) {
			if (!r.exc) {
				frm.reload_doc();
			}
		},
		freeze: true,
		freeze_message: __('Updating the Request..!')
	});
};
function is_valid_verification_code(code){
	const code_expression = /^\d{6}(\s*,\s*\d{6})*$/;
	if (code_expression.test(code))  return true;

	return false;
}