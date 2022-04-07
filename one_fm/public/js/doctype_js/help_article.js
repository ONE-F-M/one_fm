frappe.ui.form.on('Help Article', {
    refresh:function(frm){
      // set query
      set_query(frm)
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
