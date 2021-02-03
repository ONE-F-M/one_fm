frappe.ui.form.on('Supplier', {
	refresh(frm) {
		cur_frm.set_query("group", "supplier_group_table", function(doc, cdt, cdn) {
	      var d = locals[cdt][cdn];
	      return {
	          filters: [
	              ['Item Group', 'parent_item_group', '=', 'All Item Groups']
	          ]
	      }
	  });
	  cur_frm.set_query("subgroup", "supplier_group_table", function(doc, cdt, cdn) {
	      var d = locals[cdt][cdn];
	      return {
	          filters: [
	              ['Item Group', 'parent_item_group', '=', d.group]
	          ]
	      }
	  });
	},
	status: function(frm) {
		if (frm.doc.status == 'Enable') {
			frm.set_value("disabled", 0);
		}
		else {
			frm.set_value("disabled", 1);
		}
  },
	supplier_group: function(frm) {
		if(frm.doc.supplier_group){
			frappe.db.get_value('Supplier Group', frm.doc.supplier_group, 'supplier_naming_series', function(r) {
				if(r.supplier_naming_series){
					frm.set_value('naming_series', r.supplier_naming_series);
				}
				else{
					frm.set_value('naming_series', 'SUP-.#######');
				}
			});
		}
		else{
			frm.set_value('naming_series', 'SUP-.#######');
		}
	}
})
