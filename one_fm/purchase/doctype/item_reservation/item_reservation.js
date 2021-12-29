// Copyright (c) 2021, omar jaber, Anthony Emmanuel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Reservation', {
	refresh: function(frm) {
        // set company
        if(!frm.doc.company){
            frm.set_value('company', frappe.defaults.get_default('company'));
        }
	},
    from_date: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
    to_date: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
    checkDateDiff: (frm)=>{
        // check backdating
        if(frm.doc.from_date > frm.doc.to_date){
            frm.set_value('from_date', '');
            frm.set_value('to_date', '');
            frappe.throw(__(
                {
                    title:'Invalid',
                    message:'Reserve From date cannot be after Reserver To date.'
                }
            ))
        }
    }

});
