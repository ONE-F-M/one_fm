frappe.ui.form.on('Stock Entry', {
  refresh(frm) {
    set_stock_entry_type_for_issuer(frm);
  },
  onload(frm) {
    if(frappe.user.has_role('Stock Issuer')){
      frm.events.remove_stock_entry_type_create_btn(frm);
    }
  },
  remove_stock_entry_type_create_btn(frm) {
		frm.fields_dict.stock_entry_type.$wrapper.on("keyup", () => {
			setTimeout(()=>{
				var list_tags = frm.fields_dict.stock_entry_type.$wrapper.find('ul li')
				for (let list_tag of list_tags) {
					if (list_tag.innerText === __(" Create a new Stock Entry Type")) {
						list_tag.remove();
					}
				}
			}, 1000);
		});
	},
})

var set_stock_entry_type_for_issuer = function(frm) {
  if(frappe.user.has_role('Stock Issuer')){
    set_stock_entry_type_filter(frm, ["Material Issue"]);
    frappe.db.get_value("Stock Entry Type", {"purpose": "Material Issue"}, "name").then(res=>{
      if(res.message && res.message.name){
        frm.set_value('stock_entry_type', res.message.name);
      }
    });
  }
}

var set_stock_entry_type_filter = function(frm, purpose) {
  // purpose should be a list of value
  frm.set_query("stock_entry_type", function() {
      return {
          filters:{
              purpose: ['in', purpose]
          }
      };
  });
}

frappe.ui.form.on('Stock Entry Detail', {
    t_warehouse(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.t_warehouse){
            frappe.db.get_value("Warehouse", row.t_warehouse, 'allow_zero_valuation_rate').then(res=>{
                if (res.message){
                    row.allow_zero_valuation_rate = res.message.allow_zero_valuation_rate;
                    row.basic_rate = 0;
                    row.basic_amount = 0;
                    row.amount = 0;
                    row.valuation_rate = 0;
                    row.additional_cost = 0;
                    frm.refresh_field('items');
                }
            })

        }
    },

    expense_account(frm, cdt, cdn){
        let row = locals[cdt][cdn];
        if (frm.doc.stock_entry_type === "Material Issue"){
            frappe.db.get_value("Item", row.item_code, "difference_account").then(res=>{
                row.expense_account = res.message.difference_account
                 frm.refresh_field('items');
            })
        }
    }
})
