frappe.listview_settings["Wiki Page"] = {
    onload: function (list_view) {
		list_view.page.add_inner_button(__("Boost Lumina Knowledge"), function () {
            frappe.call({
                method: "one_fm.wiki_chat_bot.main.queue_fetch_wiki_and_add_to_bot_memory",
                callback: function (r) {
                    if (r.message === "Done") {
                        frappe.show_alert({
                            message: __("Bot memory turbocharged !"),
                            indicator: "blue",
                        });
                    }
                },
            });
		
		});
	},

}

