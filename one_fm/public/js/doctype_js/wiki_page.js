frappe.ui.form.on('Wiki Page', {
    title: function(frm){
        frm.trigger('slugify');
    },
    slugify: function(frm){
        let slugify = frm.doc.title;
        slugify = slugify.toLowerCase()
        slugify = slugify.trim()
        slugify = slugify.replace(/[^\w\s-]/g, '')
        slugify = slugify.replace(/[\s_-]+/g, '-')
        slugify = slugify.replace(/^-+|-+$/g, '');
        frm.set_value('route', 'wiki/'+slugify);
    }
  });
  