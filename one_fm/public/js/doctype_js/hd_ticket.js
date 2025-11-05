frappe.ui.form.on("HD Ticket", {
  refresh: function (frm) {
    add_dev_ticket_button(frm);
    add_github_issue_button(frm);
    add_pathfinder_log_button(frm);
  },
});

const add_pathfinder_log_button = (frm) => {
  if (
    frm.doc.ticket_type === "Feature Request" &&
    frappe.user.has_role("Business Analyst")
  ) {
    frm.add_custom_button(
      "Pathfinder Log",
      () => {
        frappe.call({
          method: "one_fm.overrides.hd_ticket.create_pathfinder_log",
          args: {
            hd_ticket_name: frm.doc.name,
          },
          callback: function (r) {
            if (r.message) {
              frappe.msgprint({
                message: __(
                  "Pathfinder Log <a href='/app/pathfinder-log/{0}'>{0}</a> created"
                , [r.message]),
                title: __("Pathfinder Log Created"),
                indicator: "green",
              });
              frm.reload_doc();
            }
          },
        });
      },
      "Create"
    );
  }
};

const add_github_issue_button = (frm) => {
  if (frm.doc.ticket_type == "Bug") {
    if (frm.doc.custom_github_issue_url) {
      if (!document.querySelector("#github_issue_span")) {
        let el = `<span id="github_issue_span">GitHub Issue has been created</span><br>
        <a href="${frm.doc.custom_github_issue_url}" class="btn btn-primary" target="_blank">View GitHub Issue</a>`;
        frm.dashboard.add_section(el, __("GitHub Issue"));
      }
    } else if (["Open", "Replied"].includes(frm.doc.status) && frappe.session.user==frm.doc.custom_bug_buster) {
      frm.add_custom_button(
        "GitHub Issue",
        () => {
          let d = new frappe.ui.Dialog({
            title: __("New GitHub Issue"),
            fields: [
              {
                label: __("Environment"),
                fieldname: "environment",
                fieldtype: "Select",
                options: ["Production", "Staging", "Test Production"],
                reqd: 1,
              },
              {
                label: __("Problem Description"),
                fieldname: "problem_description",
                fieldtype: "Text Editor",
                default: frm.doc.description,
              },
              {
                label: __("Steps to Reproduce"),
                fieldname: "steps_to_reproduce",
                fieldtype: "Text Editor",
                reqd: 1,
                default: `<p>1. [First step] </p><p><br></p><p>2. [Second step] </p><p><br></p><p>3. [Specific action that causes the issue] </p>`
              },
              {
                label: __("Expected Result"),
                fieldname: "expected_result",
                fieldtype: "Text Editor",
                reqd: 1,
                default: "<p>[What you expected to happen]</p>"
              },
              {
                label: __("Actual Result"),
                fieldname: "actual_result",
                fieldtype: "Text Editor",
                reqd: 1,
                default: "<p>[What actually happens - include error messages/screenshots]</p>"
              },
              {
                label: __("Technical Context"),
                fieldname: "technical_context",
                fieldtype: "Section Break",
              },
              {
                label: __("Affected DocType(s)"),
                fieldname: "affected_doctypes",
                fieldtype: "Small Text",
                default: "[Specific ERPNext doctypes involved]"
              },
              {
                label: __("Affected Files"),
                fieldname: "affected_files",
                fieldtype: "Small Text",
                default: "[If known - specific Python/JS files]"
              },
              {
                label: __("Additional Information"),
                fieldname: "additional_information",
                fieldtype: "Section Break",
              },
              {
                label: __("Error Logs"),
                fieldname: "error_logs",
                fieldtype: "Text Editor",
                default: "<p>[Paste relevant error logs]</p>"
              },
              {
                label: __("Browser/System Info"),
                fieldname: "browser_system_info",
                fieldtype: "Text Editor",
                default: "<p>[If frontend issue]</p>"
              },
              {
                label: __("DataContext"),
                fieldname: "data_context",
                fieldtype: "Text Editor",
                default: "<p>[Specific records/data involved]</p>"
              },
            ],
            primary_action_label: __("Create Issue"),
            primary_action(values) {
              const description = `
                ### Environment:
                ${values.environment}

                ### Problem Description:
                ${values.problem_description}

                ### Steps to Reproduce:
                ${values.steps_to_reproduce}

                ### Expected Result:
                ${values.expected_result}

                ### Actual Result:
                ${values.actual_result}

                ### Technical Context:
                **Affected DocType(s):** ${values.affected_doctypes}
                **Affected Files:** ${values.affected_files}

                ### Additional Information:
                **Error Logs:**
                \`\`\`
                ${values.error_logs}
                \`\`\`

                **Browser/System Info:**
                ${values.browser_system_info}

                **DataContext:**
                ${values.data_context}
              `;

              frappe.call({
                method: "one_fm.overrides.hd_ticket.create_github_issue",
                freeze: true,
                freeze_message: "Creating GitHub Issue",
                args: {
                  name: frm.doc.name,
                  description: description,
                },
                callback: function (r) {
                  if (r.message.status == "success") {
                    frappe.msgprint("GitHub issue created successfully");
                    frm.refresh();
                    frm.reload_doc();
                  }
                },
              });
              d.hide();
            },
          });
          d.show();
        },
        "Create"
      );
    }
  }
};

const add_dev_ticket_button = (frm) => {
  if (
    frappe.user.has_role("System Manager") ||
    frappe.user.has_role("Issue User")
  ) {
    if (frm.doc.custom_dev_ticket) {
      // If Dev Ticket is already created
      if (!document.querySelector("#dev_ticket_span")) {
        let el = `<span id="dev_ticket_span">Dev Ticket has been created</span><br>
        <a href="${frm.doc.custom_dev_ticket}" class="btn btn-primary" target="_blank">View Dev Ticket</a>`;
        frm.dashboard.add_section(el, __("Dev Ticket"),);
      }
    } else if (["Open", "Replied"].includes(frm.doc.status)) {
      frm.add_custom_button(
        "Dev Ticket",
        () => {
          frappe.confirm(
            "Are you sure you create Dev Ticket?",
            () => {
              frappe.call({
                method: "one_fm.overrides.hd_ticket.create_dev_ticket",
                freeze: true,
                freeze_message: "Creating Dev Ticket",
                args: { name: frm.doc.name, description: frm.doc.description },
                callback: function (r) {
                  if (r.message.status == "success") {
                    frappe.msgprint(
                      "Dev ticket created successfully"
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
