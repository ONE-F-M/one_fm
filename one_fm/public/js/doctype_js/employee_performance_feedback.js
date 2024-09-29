frappe.ui.form.on('Employee Performance Feedback', {
    employee:(frm)=>{
        if(!frm.doc.company){
            frm.set_value('company',frappe.defaults.get_user_default('Company'))
            frm.refresh_field('company')   
        }
        
    },
    refresh:(frm)=>{
       if(frm.is_new()){
            frm.set_value('company',frappe.defaults.get_user_default('Company'))
            frm.refresh_field('company')   
       }
    },
    
})