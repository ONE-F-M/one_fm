frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
        if(frm.doc.customer){
            frm.set_query("project", function() {
                return {
                    filters:{
                        customer: frm.doc.customer
                    }
                };
            });
            frm.refresh_field("project");
        }
    }
});