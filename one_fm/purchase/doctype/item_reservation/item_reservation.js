// Copyright (c) 2021, omar jaber, Anthony Emmanuel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Reservation', {
	refresh: function(frm) {

	},
    from: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
    to: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
    checkDateDiff: (frm)=>{
        // check backdating
        if(frm.doc.from > frm.doc.to){
            frm.set_value('from', '');
            frm.set_value('to', '');
            frappe.throw(__(
                {
                    title:'Invalid',
                    message:'Reserve From date cannot be after Reserver To date.'
                }
            ))
        }
    }

});
