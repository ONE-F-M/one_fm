

frappe.ui.form.on('Salary Structure Assignment', {
    salary_structure: function(frm){
        fetch_salary_component(frm)
    },
    base: function(frm){
        fetch_salary_component(frm)
    },
})

function fetch_salary_component(frm){
    if(frm.doc.salary_structure){
        return frappe.call({
            method: 'one_fm.api.doc_methods.salary_structure_assignment.fetch_salary_component',
            args:{salary_structure: frm.doc.salary_structure, base:frm.doc.base},
            freeze: true,
            freeze_message: `Processing`,
            callback: function(r) {
                var components = r.message
                frm.clear_table('salary_structure_components');
                components.forEach((component, i) => {
                  var sal_com = frm.add_child('salary_structure_components');
                  sal_com.salary_component = component["salary_component"]
                  sal_com.amount = component["amount"]
                });
                frm.refresh_fields();
            }
        })
    }
}
