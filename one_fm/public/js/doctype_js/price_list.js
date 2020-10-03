frappe.ui.form.on('Price List', {
    validate: function(frm){
        if(frm.doc.project){
            frappe.call({
				method: 'frappe.client.get_value',
				args:{
					'doctype':'Price List',
					'filters':{
						'project': frm.doc.project,
						'enabled': 1
					},
					'fieldname':[
						'name'
					]
				},
				callback:function(s){
					if (!s.exc) {
						if(s.message){
                            msgprint('Price List with project already exists')
                            validated = false;
						}
					}
				}
			});
        }
    }
});