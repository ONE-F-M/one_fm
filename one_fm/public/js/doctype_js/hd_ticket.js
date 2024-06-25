frappe.ui.form.on("HD Ticket", {
  refresh: function (frm) {
    add_pivotal_tracker_button(frm);
  },
});

const add_pivotal_tracker_button = (frm) => {
  if (
    frappe.user.has_role("System Manager") ||
    frappe.user.has_role("Issue User")
  ) {
    if (frm.doc.pivotal_tracker) {
      // If Pivotal Tracker story is already created
      if (!document.querySelector("#pivotal_tracker_span")) {
        let el = `<span id="pivotal_tracker_span">HD Ticket has been logged to Pivotal tracker</span><br>
        <a href="${frm.doc.pivotal_tracker}" class="btn btn-primary" target="_blank">Pivotal Tracker</a>`;
        frm.dashboard.add_section(el, __("Pivotal Tracker"));
      }
    } else if (["Open", "Replied"].includes(frm.doc.status)) {
      frm.add_custom_button(
        "Pivotal Tracker Story",
        () => {
          frappe.confirm(
            "Are you sure you create Pivotal Tracker story?",
            () => {
              frappe.call({
                method: "one_fm.overrides.hd_ticket.create_pivotal_tracker_story",
                freeze: true,
                freeze_message: "Creating Pivotal Tracker Story",
                args: { name: frm.doc.name, description: frm.doc.description },
                callback: function (r) {
                  if (r.message.status == "success") {
                    frappe.msgprint(
                      "Pivotal Tracker story created successfully"
                    );
                    frm.refresh();
                    frm.reload_doc();
                  }
                },
              });
            },
            () => null
          );
        },
        "Create"
      );
    }
  }
};
