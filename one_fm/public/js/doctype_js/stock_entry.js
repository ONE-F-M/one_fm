frappe.ui.form.on('Stock Entry', {
  refresh(frm) {
    set_stock_entry_type_for_issuer(frm);
    set_store_keeper_warehouses(frm);
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
  stock_entry_type(frm){
    frm.set_value('from_warehouse', '');
    frm.set_value('to_warehouse', '');
    set_store_keeper_warehouses(frm);
  },
  project(frm) {
    auto_fill_project(frm);
  },
  from_warehouse(frm){
    frm.trigger("project");
  },
  to_warehouse(frm){
    frm.trigger("project");
  }
})

frappe.ui.form.on('Stock Entry Detail', {
  items_add(doc, cdt, cdn) {
    var row = frappe.get_doc(cdt, cdn);
    doc.script_manager.copy_from_first_row("items", row, ["project"]);
	}
});

var auto_fill_project = function(frm) {
  if (frm.doc.project && frm.doc.items && frm.doc.items.length) {
    $.each(frm.doc.items || [], function(i, item) {
      frappe.model.set_value("Stock Entry Detail", item.name, "project", frm.doc.project);
    });
  }
};

var set_store_keeper_warehouses = function(frm) {
  frappe.call({
    method: 'one_fm.overrides.stock_entry.get_store_keeper_warehouses',
    callback: function(r) {
      var warehouse_field = "from_warehouse";
      if(frm.doc.stock_entry_type == "Material Receipt"){
        warehouse_field = "to_warehouse";
      }
      frm.set_df_property(warehouse_field, "read_only", false);
      if(r.message && r.message.length > 0){
        if(r.message.length == 1){
          frm.set_value(warehouse_field, r.message[0]);
          frm.set_df_property(warehouse_field, "read_only", true);
        }
        set_warehouse_filter(frm, warehouse_field, r.message)
      }
    }
  })
};

var set_warehouse_filter = function(frm, warehouse_field, warehouses) {
  // warehouses should be a list of value
  frm.set_query(warehouse_field, function() {
      return {
          filters:{
              name: ['in', warehouses]
          }
      };
  });

  // Set item line warehouse field
  var items_warehouse_field = "s_warehouse";
  if(warehouse_field == "to_warehouse"){
    items_warehouse_field = "t_warehouse";
  }
  // Set warehouse filter in items line
  frm.set_query(items_warehouse_field, "items", function() {
      return {
          filters:{
              name: ['in', warehouses]
          }
      };
  });
}

var set_stock_entry_type_for_issuer = function(frm) {
  if(frappe.user.has_role('Stock Issuer')){
    set_stock_entry_type_filter(frm, ["Material Issue", "Material Receipt"]);
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
