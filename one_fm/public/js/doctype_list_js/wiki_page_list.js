frappe.listview_settings["Wiki Page"] = {
    onload: function (list_view) {
		list_view.page.add_inner_button(__("Boost Bot Knowledge"), function () {
            frappe.call({
                method: "one_fm.wiki_chat_bot.main.fetch_wiki_and_add_to_bot_memory",
                callback: function (r) {
                    if (r.message === "Done") {
                        frappe.show_alert({
                            message: __("Bot memory turbocharged !"),
                            indicator: "blue",
                        });
                        cur_dialog.hide();
                    }
                },
            });
		
		});
	},

}

