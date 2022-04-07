frappe.ui.form.on('Help Article', {
    refresh:function(frm){
      // set query
      set_query(frm);
      custom_buttons(frm);
    },
    category: function(frm){
      frm.set_query('subcategory', () => {
          return {
              filters: {
                  category: frm.doc.category,
                  is_subcategory: 1
              }
          }
      })
    }
});

// SET QUERY
let set_query = frm => {
  // filters category for notself and not sub category
  frm.set_query('category', () => {
      return {
          filters: {
              is_subcategory: 0
          }
      }
  })
}

// custom buttons
let custom_buttons = frm => {
  if (!frm.is_new()){
    frm.add_custom_button('Articles in '+frm.doc.category, ()=>{
      frappe.set_route('List', 'Help Article', {'category':frm.doc.category});
    }, 'View')
  }
}
