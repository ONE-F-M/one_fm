from frappe import _

def get_data(data=None):
    from hrms.hr.doctype.leave_application.leave_application_dashboard import get_data as _get_data
    data = _get_data()

    # Append Accommodation Leave Movement
    data.setdefault('transactions', []).append({
        'label': _('Accommodation'),
        'items': ['Accommodation Leave Movement']
    })

    return data
