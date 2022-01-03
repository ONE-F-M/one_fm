this.frm.dashboard.add_transactions([
    {
        'items': [
            'Customer Asset'
            
        ],
        'label': 'Related'
    },
    
]);
frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
		approve_if_signed(frm);
	}
});

var approve_if_signed = function(frm){
	if(frm.doc.status == "Completed"){
		if(frm.doc.authority_signature == undefined){
			frappe.throw(__('Please Sign the form to Accept the Request'))
		};
	}
};