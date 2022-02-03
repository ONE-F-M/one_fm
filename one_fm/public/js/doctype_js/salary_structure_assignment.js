frappe.ui.form.on('Salary Structure Assignment', {
<<<<<<< HEAD
    // refresh: function(frm) {

	  // }
});
=======
    base: function(frm) {
        console.log("Here")
        set_salary_structure_to_salary_details(frm);
      }
});
var set_salary_structure_to_salary_details = function(frm) {
    frm.clear_table('salary_structure_components');
    let total_amount = 0;
    let base = frm.doc.base
    if(frm.doc.salary_structure && base){
      frappe.call({
        method: 'frappe.client.get',
        args: {
          doctype: 'Salary Structure',
          filters: {'name': frm.doc.salary_structure}
        },
        callback: function(r) {
          if(r && r.message){
            if(r.message.earnings){
              r.message.earnings.forEach((item, i) => {
                console.log(item.amount_based_on_formula)
                if(item.amount_based_on_formula && item.formula){
                  let formula = item.formula;
                  const percent = formula.split("*")[1];
                  let amount = parseInt(base)*parseFloat(percent);
                  console.log(amount)
                  if(amount!=0){
                    let salary = frappe.model.add_child(frm.doc, 'Salary Component Table', 'salary_structure_components');
                    frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
                    frappe.model.set_value(salary.doctype, salary.name, 'amount', amount);
                  }
                } else {
                  if(item.amount!=0){
                    let salary = frappe.model.add_child(frm.doc, 'Salary Component Table', 'salary_structure_components');
                    frappe.model.set_value(salary.doctype, salary.name, 'salary_component', item.salary_component);
                    frappe.model.set_value(salary.doctype, salary.name, 'amount', item.amount);
                  } 
                }
              });
            }
          }
          frm.refresh_field('one_fm_salary_details');
        }
      });
    }
    frm.refresh_field('one_fm_salary_details');
  };
>>>>>>> 0e4be0b4 (Modify Salary Structure Assignment to inculde Salary Component details)
