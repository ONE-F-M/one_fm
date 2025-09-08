frappe.ui.form.on('Roster Employee Actions', {
    refresh(frm) {
        frm.add_custom_button(__('Take Action'), function() {
            const employeeID = encodeURIComponent(frm.doc.employee_id || '');
            const shift = encodeURIComponent(frm.doc.shift || '');

            const url = `/app/roster?main_view=roster&sub_view=basic&roster_type=basic&employee_id=${employeeID}&shift=${shift}`;
            window.open(url, '_blank');
        });
    }
});
