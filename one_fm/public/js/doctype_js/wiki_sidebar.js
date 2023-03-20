frappe.ui.form.on("Wiki Sidebar", {
    refresh: function (frm) {
      frm.set_query("type", "sidebar_items", function () {
        return {
          filters: {
            name: ["in", ["Wiki Page", "Wiki Sidebar"]],
          },
        };
      });
    },

});

frappe.ui.form.on('Wiki Sidebar Item', {
  item: function(frm, cdt, cdn) { 
        let doc = locals[cdt][cdn];
        if (doc.type == "Wiki Sidebar" && doc.title !== null ){
          let slugify = doc.title;
          slugify = slugify.toLowerCase()
          slugify = slugify.trim()
          slugify = slugify.replace(/[^\w\s-]/g, '')
          slugify = slugify.replace(/[\s_-]+/g, '-')
          slugify = slugify.replace(/^-+|-+$/g, '');
          frappe.model.set_value(cdt, cdn, "route", 'wiki/sidebar/' + slugify)
        }
    },
});
