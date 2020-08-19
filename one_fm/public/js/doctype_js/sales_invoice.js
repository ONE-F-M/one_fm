frappe.ui.form.on('Sales Invoice', {
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
        frm.fields_dict['items'].grid.get_field('income_account').get_query = function() {
            return {    
                filters:{
                    root_type:'Income',
                    is_group: 0
                }
            }
        }
        frm.refresh_field("items");
    }
});