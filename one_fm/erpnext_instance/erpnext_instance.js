// Copyright (c) 2022, Anthony Emmanuel and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERPNext Instance', {
	refresh: function(frm) {

	},
  subscription_start_date: (frm)=>{
    frm.set_value('subscription_end_date', subscription_type(frm, frm.doc.subscription_start_date));
  },
  subscription_type: (frm)=>{
    frm.set_value('subscription_end_date', subscription_type(frm, frm.doc.subscription_start_date));
  },
  trash: (frm)=>{
    frappe.confirm('Are you sure you want to proceed?',
        () => {
            // action to perform if Yes is selected
        }, () => {
            // action to perform if No is selected
            return
        })
  }
});


const subscription_type = (frm, type) => {
  let endDate = "";
  if(frm.doc.subscription_type=='Monthly'){
    endDate = moment(frm.doc.subscription_start_date).add(1, 'M')//._d.toLocaleDateString();
  } else if(frm.doc.subscription_type=='Quaterly'){
    endDate = moment(frm.doc.subscription_start_date).add(3, 'M')//._d.toLocaleDateString();
  } else if(frm.doc.subscription_type=='Half-yearly'){
    endDate = moment(frm.doc.subscription_start_date).add(6, 'M')//._d.toLocaleDateString();
  } else if(frm.doc.subscription_type=='Yearly'){
    endDate = moment(frm.doc.subscription_start_date).add(12, 'M')//._d.toLocaleDateString();
  }

  return endDate;

}
