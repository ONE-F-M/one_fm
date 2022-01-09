// Copyright (c) 2021, omar jaber, Anthony Emmanuel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Reservation', {
	setup: (frm)=>{
		frm.set_query('item_code', () => {
			return {

					query: 'one_fm.purchase.doctype.item_reservation.item_reservation.get_rfm_items',
					doctype: 'Request for Material',
					txt: frm.doc.rfm
			}
		})
	},
	refresh: (frm)=>{
        // set company
        if(!frm.doc.company){
            frm.set_value('company', frappe.defaults.get_default('company'));
        }
		// add custom buttons
		// frm.trigger('custom_buttons')
	},
    from_date: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
    to_date: (frm)=>{
        // check date difference between from and to Reservation
        frm.trigger('checkDateDiff');
    },
	rfm: (frm)=>{

	},
	get_rfm_items: (frm)=>{
		if(frm.doc.rfm){
			console.log('searching')
			frappe.db.get_doc('Request for Material', frm.doc.rfm).then(res=>{
				frm.set_query('item_code', () => {
				    return {
				        filters: {
				            query: 'one_fm.purchase.doctype.item_reservation.item_reservation.get_rfm_items',

				        }
				    }
				})
			})
		}
	},
    checkDateDiff: (frm)=>{
        // check backdating
        if(frm.doc.from_date > frm.doc.to_date){
            frm.set_value('from_date', '');
            frm.set_value('to_date', '');
            frappe.throw(__(
                {
                    title:__('Invalid'),
                    message:__('Reserve From date cannot be after Reserver To date.')
                }
            ))
        }
    },
	custom_buttons: (frm)=>{
		// add custom action buttons
		if(frm.doc.docstatus==1 && frm.doc.status=='Active'){
			// update qty
			frm.add_custom_button(__('Update QTY'), () => {
				frm.trigger('update_qty');
            });
			frm.change_custom_button_type(__('Update QTY'), null, 'primary');

			// Issue
			frm.add_custom_button(__('Issue QTY'), () => {
				frm.trigger('issue_qty');
            });
			frm.change_custom_button_type(__('Issue QTY'), null, 'warning');

			// close reservation
			frm.add_custom_button(__('Close Reservation'), () => {
				frm.trigger('close_reservation');
            });
			frm.change_custom_button_type(__('Close Reservation'), null, 'secondary');
		}
	},
	update_qty: (frm)=>{
		let d = new frappe.ui.Dialog({
	    title: __('Update Reserved Quantity'),
	    fields: [
	        {
	            label: __('Update Type'),
	            fieldname: 'type',
	            fieldtype: 'Select',
				options: [__('Increase by'), __('Reduce by')],
				reqd:1
	        },
	        {
	            label: __('Quantity'),
	            fieldname: 'qty',
	            fieldtype: 'Int',
				reqd:1,
				default:1
	        }
	    ],
	    primary_action_label: __('Submit'),
	    primary_action(values) {
			// validate values
			if(values.qty<=0){
				frappe.throw(__('Quantity must be greater than 0'))
			} else {
				// check quantities
				get_stock_balance(frm).then(res=>{
					if(res.message.total){
						let total = res.message.total;
						d.hide(); // hide modal
						if(values.type==__('Increase by')){
							// increase block
							if(total<(values.qty+frm.doc.qty)){
								frappe.throw(__(`
									Insufficient balance, available QTY
									<b>${total}</b> is less than reserved QTY <b>${frm.doc.qty}</b>
									+ additional <b>${values.qty}.</b>
									`
								))
							} else {
								// update qty
								frm.call('update_reservation', {
									field:'qty', type:'increase', qty:values.qty
								}).then(r => {
							        if (r.message) {
										frm.refresh();
							            frappe.msgprint(__(`
											Reserved QTY increased to <b>${r.docs[0].qty}</b> successfully.
										`))
							        }
							    })
							}
							// end increase block
						} else if(values.type==__('Reduce by')){
							// reduce block
							if(values.qty>=frm.doc.qty){
								frappe.throw(__(`
									QTY to be reduced cannot be greater than or equal to reserved QTY.
								`))
							} else if(total>=(frm.doc.qty-values.qty)){
								frm.call('update_reservation', {
									field:'qty', type:'reduce', qty:values.qty
								}).then(r => {
							        if (r.message) {
										frm.refresh();
							            frappe.msgprint(__(`
											Reserved QTY reduced to <b>${r.docs[0].qty}</b> successfully.
										`))
							        }
							    })

							}
						}
						// end reduce block
					} else {
						frappe.throw(__('An error occurred'))
					}
				});
			}
	    }
	});
		// show Dialog
		d.show();
	},
	issue_qty: (frm)=>{
		// issue out qty from reservation
		let d = new frappe.ui.Dialog({
	    title: __('Update Issued Quantity'),
	    fields: [
	        {
	            label: __('Issue Type'),
	            fieldname: 'type',
	            fieldtype: 'Select',
				options: [__('Increase by'), __('Reduce by')],
				reqd:1,
				default: __('Reduce by')
	        },
	        {
	            label: __('Quantity'),
	            fieldname: 'qty',
	            fieldtype: 'Int',
				reqd:1,
				default:1
	        }
	    ],
	    primary_action_label: __('Submit'),
	    primary_action(values) {
			// validate values
			if(values.qty<=0){
				frappe.throw(__('Quantity must be greater than 0'))
			} else {
				// check quantities
					d.hide(); // hide modal
					if(values.type==__('Increase by')){
						// increase block
						if(frm.doc.qty<values.qty || ((values.qty+frm.doc.issued_qty) > frm.doc.qty)){
							frappe.throw(__(`
								QTY to be issued <b>${values.qty}</b> must be less or equal to
								reserved QTY <b>${frm.doc.qty}</> or your value may have exceed issued QTY.
							`))
						} else {
							// update qty
							frm.call('update_issue', {
								field:'issued_qty', type:'increase', qty:values.qty
							}).then(r => {
						        if (r.message) {
									frm.refresh();
						            frappe.msgprint(__(`
										Issued QTY updated to <b>${r.docs[0].issued_qty}</b> successfully.
									`))
						        }
						    })
						}
						// end increase block
					} else if(values.type==__('Reduce by')){
						// reduce block
						if(values.qty>=frm.doc.qty || values.qty<=0 ||
								((values.qty-frm.doc.issued_qty)>frm.doc.issued_qty)){
							frappe.throw(__(`
								QTY to be reduced cannot be greater than reserved QTY nor <br>
								greater than issued QTY.
							`))
						} else if(frm.doc.qty>=values.qty){
							frm.call('update_issue', {
								field:'issued_qty', type:'reduce', qty:values.qty
							}).then(r => {
						        if (r.message) {
									frm.refresh();
									console.log(r)
						            frappe.msgprint(__(`
										Issued QTY updated to <b>${r.docs[0].issued_qty}</b> successfully.
									`))
						        }
						    })

						}
					}
						// end reduce block
					// }
			}
	    }
	});
		// show Dialog
		d.show();
	},
	close_reservation: (frm)=>{
		// complete reservation
		frappe.confirm('Are you sure you want to proceed?',
		    () => {
				frm.call('close_reservation').then(r => {
					if (r.message) {
						frm.refresh();
						frappe.msgprint(__(`
							Reserved has been closed successfully.
						`))
					}
				})
		    }, () => {
		        // action to perform if No is selected
	    })
	}

});


const get_stock_balance = (frm)=>{
	// get item balance
	return frappe.call({
		method: "one_fm.purchase.doctype.item_reservation.item_reservation.get_item_balance",
		args:{item_code:frm.doc.item_code},
		freeze: true,
        freeze_message: `Processing`,
		callback: function(r) {
			return r
		}
	})
}
