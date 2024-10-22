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
    },
    refresh(frm){
        frm.add_custom_button(__('Charge Lumina !'), function () {
            frappe.call({
                method: "one_fm.wiki_chat_bot.main.add_wiki_page_to_bot_memory",
                args: {"doc": cur_frm.doc},
                callback: function (r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __("Lumina memory turbocharged !"),
                            indicator: "blue",
                        });
                    }
                },
            });
        }
      ).addClass('btn-success');
      frm.add_custom_button(__('Charge Lumina by Gemini!'), function () {
        frappe.call({
            method: "one_fm.wiki_chat_bot.main.add_wiki_page_to_bot_memory_by_gemini",
            args: {"doc": cur_frm.doc},
            callback: function (r) {
                if (r.message) {
                    frappe.show_alert({
                        message: __("Lumina memory turbocharged by gemini !"),
                        indicator: "blue",
                    });
                }
            },
        });
    }
  ).addClass('btn-success');
    }
  });
  