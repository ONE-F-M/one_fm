def daily_indemnity_allocation_builder():
    query = """
        select emp.name, emp.date_of_joining, emp.indemnity_policy
        from `tabEmployee` emp
        left join `tabIndemnity Allocation` ia on emp.name = ia.employee and ia.docstatus = 1 and emp.status = 'Active'
        where ia.employee is NULL
    """
    employee_list = frappe.db.sql(query, as_dict=True)
    frappe.enqueue(indemnity_allocation_builder, timeout=600, employee_list=employee_list)

def indemnity_allocation_builder(employee_list):
    for employee in employee_list:
        create_indemnity_allocation(employee)

def create_indemnity_allocation(employee):
    indemnity_allcn = frappe.new_doc('Indemnity Allocation')
    indemnity_allcn.employee = employee.name
    indemnity_allcn.from_date = employee.date_of_joining
    indemnity_allcn.new_indemnity_allocated = 30/365
    indemnity_allcn.total_indemnity_allocated = 30/365
    indemnity_allcn.submit()

def allocate_daily_indemnity():
    # Get List of Indemnity Allocation for today
    allocation_list = frappe.get_all("Indemnity Allocation", filters={"expired": ["!=", 1]}, fields=["name"])
    for alloc in allocation_list:
        allow_allocation = True
        allocation = frappe.get_doc('Indemnity Allocation', alloc.name)
        # Check if employee absent today then not allow allocation for today
        is_absent = frappe.db.sql("""select name, status from `tabAttendance` where employee = %s and
            attendance_date = %s and docstatus = 1 and status = 'Absent' """,
			(allocation.employee, getdate(nowdate())), as_dict=True)
        if is_absent and len(is_absent) > 0:
            allow_allocation = False

        # Check if employee on leave today and allow allocation for today
        leave_appln = frappe.db.sql("""select name, status, leave_type from `tabLeave Application` where employee = %s and
            (%s between from_date and to_date) and docstatus = 1 and status = 'Rejected'""",
			(allocation.employee, getdate(nowdate())), as_dict=True)
        if leave_appln and len(leave_appln) > 0:
            allow_allocation = False

        if allow_allocation:
            # Set Daily Allocation
            allocation.new_indemnity_allocated = 30/365
            allocation.total_indemnity_allocated = allocation.total_indemnity_allocated+allocation.new_indemnity_allocated
            allocation.save()

def validate_leave_proof_document_requirement(doc, method):
    '''
        Function to validate Is Proof Document Required Flag in Leave Application
        Triger form Validate hook of Leave Application
    '''

    if doc.leave_type and doc.status in ['Open', 'Approved']:
        doc.is_proof_document_required = frappe.db.get_value('Leave Type', doc.leave_type, 'is_proof_document_required')
        if doc.is_proof_document_required and not doc.proof_document:
            frappe.throw(_("Proof Document Required for {0} Leave Type.!".format(doc.leave_type)))