frappe.ui.form.on('Roster Employee Actions', {
    refresh(frm) {
        frm.add_custom_button(__('Take Action'), function() {
            const employeeID = encodeURIComponent(frm.doc.employee_id || '');
            const shift = encodeURIComponent(frm.doc.shift || '');
            const selectedDate = frm.doc.start_date ? new Date(frm.doc.start_date) : new Date();

            const targetMonth = selectedDate.getMonth() + 1; // Months are zero-based
            const targetYear = selectedDate.getFullYear();

            const url = `/app/roster?main_view=roster&sub_view=basic&roster_type=basic&employee_id=${employeeID}&shift=${shift}&month=${targetMonth}&year=${targetYear}`;
            window.open(url, '_blank');
        });
    }
});
