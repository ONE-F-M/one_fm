

frappe.ui.form.on('Salary Structure Assignment', {
    salary_structure: function(frm){
        fetch_salary_component(frm)
    },
    base: function(frm){
        fetch_salary_component(frm)
    },
})
 
function fetch_salary_component(frm){
    if(frm.doc.base && frm.doc.salary_structure){
        return frappe.call({
            method: 'one_fm.api.doc_methods.salary_structure_assignment.fetch_salary_component',
            args:{salary_structure: frm.doc.salary_structure, base:frm.doc.base},
            freeze: true,
            freeze_message: `Processing`,
            callback: function(r) {
                var component = r.message
                frm.clear_table('salary_structure_components');
                for (let c in component){
                    var sal_com = frm.add_child('salary_structure_components');
                    sal_com.salary_component = component[c]["salary_component"]
                    sal_com.amount = component[c]["amount"]  
                }
                frm.refresh_fields();
            }
        })
    }
}