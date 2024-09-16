frappe.ui.form.on("Appraisal", {
  refresh: function (frm) {
    set_self_appraisal_permissions(frm);
  },
  employee: function (frm) {
    set_self_appraisal_permissions(frm);
  },
  appraisal_template: function (frm) {
    set_self_appraisal_permissions(frm);
  },
});

const set_self_appraisal_permissions = async (frm) => {
  frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((res) => {
      const loggedInUser = res.message.name;

      // Only 'Appraisee' can update 'Self Appraisal' section fields
      if (loggedInUser != frm.doc.employee) {
        frm.set_df_property("self_ratings", "read_only", 1);
        frm.set_df_property("reflections", "read_only", 1);
      } else {
        frm.set_df_property("self_ratings", "read_only", 0);
        frm.set_df_property("reflections", "read_only", 0);
      }
    });
};
