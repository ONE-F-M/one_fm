frappe.ui.form.on('Help Category', {
    refresh:function(frm){
      // set query
      set_query(frm)
    }
});

// SET QUERY
let set_query = frm => {
  // filters category for notself and not sub category
  frm.set_query('category', () => {
      return {
          filters: {
              name: ['!=', frm.doc.name],
              is_subcategory: 0
          }
      }
  })
}
