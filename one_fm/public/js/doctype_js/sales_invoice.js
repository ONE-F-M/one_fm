frappe.ui.form.on('Sales Invoice',{
	refresh(frm){
		var df = frappe.meta.get_docfield("Sales Invoice Item","accounting_dimensions_section",frm.doc.name);
		var df1 =frappe.meta.get_docfield("Sales Invoice Item","cost_center",frm.doc.name);
		df.hidden = 1;
		df1.reqd = 0;
		cur_frm.set_query("project", function(frm){
			if(cur_frm.doc.customer){
			  return{
				  filters:[
					  ["Project","customer", "=", cur_frm.doc.customer]
				  ]
			  };
			}
		});
	}
});
