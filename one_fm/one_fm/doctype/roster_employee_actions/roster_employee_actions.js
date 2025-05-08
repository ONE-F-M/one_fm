frappe.ui.form.on('Roster Employee Actions', {
    refresh(frm) {
        frm.fields_dict["employees_not_rostered"].grid.grid_rows.forEach(row => {
            add_action_button(row, frm);
        });

        // Also handle dynamically rendered rows
        frm.fields_dict["employees_not_rostered"].grid.on('grid-row-render', function (grid_row) {
            add_action_button(grid_row, frm);
        });
    }
});

function add_action_button(grid_row, frm) {
    const row = grid_row.doc;

    const $cell = $(grid_row.row).find('[data-fieldname="take_action"]');
    $cell.empty();

    const $btn = $(`<button class="btn btn-xs btn-primary">Take Action</button>`);
    $btn.on('click', () => {
        if (!row.employee) {
            frappe.msgprint("No employee selected.");
            return;
        }

        frappe.db.get_doc('Employee', row.employee).then(employee => {
            const url = `/app/roster?main_view=roster&sub_view=basic&roster_type=basic&employee_id=${employee.employee_id}&shift=${row.shift_allocation}`;
            window.open(url, '_blank');
        });
    });

    $cell.append($btn);
}
