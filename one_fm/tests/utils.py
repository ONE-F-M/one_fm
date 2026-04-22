import frappe
from frappe.utils import add_days, nowdate
from frappe.core.doctype.user_permission.test_user_permission import create_user
import erpnext

def get_test_employee():
    """Get or create test employee"""
    if not frappe.db.exists("Employee", {"user_id": "test_employee@example.com"}):
        return make_employee("test_employee@example.com", company="_Test Company")
    return frappe.get_doc("Employee", {"user_id": "test_employee@example.com"})

def make_employee(user, company=None, **kwargs):
    if not frappe.db.get_value("User", user):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": user,
                "first_name": user,
                "new_password": "password",
                "send_welcome_email": 0,
                "roles": [{"doctype": "Has Role", "role": "Employee"}],
            }
        ).insert()

    if not frappe.db.get_value("Employee", {"user_id": user}):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "naming_series": "EMP-",
                "name": "_T-Employee-00001",
                "first_name": user,
                "company": company or erpnext.get_default_company(),
                "user_id": user,
                "date_of_birth": "1990-05-08",
                "date_of_joining": "2013-01-01",
                "department": frappe.get_all("Department", fields="name")[0].name,
                "gender": "Female",
                "company_email": user,
                "prefered_contact_email": "Company Email",
                "prefered_email": user,
                "status": "Active",
                "employment_type": "Intern",
                "last_name": "Test",
                "one_fm_first_name_in_arabic": "اختبار",
                "one_fm_last_name_in_arabic": "الموظف",
                "one_fm_basic_salary": 1000
            }
        )
        if kwargs:
            employee.update(kwargs)
        employee.insert()
        return employee
    else:
        employee = frappe.get_doc("Employee", {"user_id": user})
        employee.update(kwargs)
        employee.status = "Active"
        employee.save()
        return employee


def get_test_leave_type(**kwargs):
    """Create test leave type"""
    leave_type_name = kwargs.get("leave_type_name", "Annual Leave")
    if frappe.db.exists("Leave Type", leave_type_name):
        frappe.delete_doc("Leave Type", leave_type_name, force=True)
    
    defaults = {
        "is_lwp": False,
        "include_holiday": False,
        "max_leaves_allowed": 1000,
        "allow_negative": True,
        "is_carry_forward": False,
        "one_fm_is_paid_sick_leave": False,
        "one_fm_is_hajj_leave": False,
        "one_fm_is_paid_annual_leave": False,
        "custom_is_maternity": False,
        "custom_update_employee_status_to_vacation": False,
        "is_proof_document_required": False,
        "allow_negative": False,
        "is_compensatory": False,
        "allow_over_allocation": False,
        "applicable_after": 0,
        "max_continuous_days_allowed": 0,
    }

    defaults.update(kwargs)

    leave_type = frappe.get_doc({
        "doctype": "Leave Type",
        "leave_type_name": leave_type_name,
        "company": "_Test Company",
        **defaults
    })
    leave_type.insert()
    return leave_type

def create_test_leave_allocation(employee, leave_type, **kwargs):
    """Create test leave allocation"""
    from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

    allocation_defaults = {
        "doctype": "Leave Allocation",
        "employee": employee.name,
        "leave_type": leave_type.name,
        "from_date": nowdate(),
        "to_date": add_days(nowdate(), 365),
        "new_leaves_allocated": 20,
        "company": "_Test Company",
    }

    allocation_defaults.update(kwargs)

    leave_allocation = LeaveAllocation(allocation_defaults)
    leave_allocation.insert()
    leave_allocation.submit()
    return leave_allocation

def create_test_company():
    # Ensure test company exists
    if not frappe.db.exists("Company", "_Test Company"):
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "_Test Company",
            "abbr": "_TC",
            "default_currency": "KWD",
            "country": "Kuwait",
            "default_language": "en"
        })
        company.insert(ignore_permissions=True)
    
    # Create and assign a default Holiday List for the company
    if not frappe.db.exists("Holiday List", "Test Holiday List"):
        # Use dates that span from last year to next year to cover any holiday dates
        from_date = add_days(nowdate(), -365)
        to_date = add_days(nowdate(), 365)
        
        holiday_list = frappe.get_doc({
            "doctype": "Holiday List",
            "holiday_list_name": "Test Holiday List",
            "company": "_Test Company",
            "from_date": from_date,
            "to_date": to_date,
            "holidays": [
                {"description": "Test Holiday", "holiday_date": nowdate()}
            ]
        })
        holiday_list.insert(ignore_permissions=True)
    
    # Set the Holiday List as default for the company
    frappe.db.set_value("Company", "_Test Company", "default_holiday_list", "Test Holiday List")

def make_leave_application(employee, from_date, to_date, leave_type, company=None, half_day=False, half_day_date=None, submit=False):
    create_user("test@example.com")

    leave_application = frappe.get_doc(
        dict(
            doctype="Leave Application",
            employee=employee,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
            half_day=half_day,
            half_day_date=half_day_date,
            company=company or erpnext.get_default_company() or "_Test Company",
            status="Open",
            leave_approver="test@example.com",
            resumption_date=add_days(to_date, 1)
        )
    ).insert()

    if submit:
        leave_application.submit()

    return leave_application

def create_test_bed_space_type(bed_space_type_name="Test Bed Space Type", **kwargs):
    """Create or get test bed space type"""
    if frappe.db.exists("Bed Space Type", bed_space_type_name):
        return frappe.get_doc("Bed Space Type", bed_space_type_name)
    
    defaults = {
        "bed_space_type": bed_space_type_name,
        "single_bed_capacity": 1,
        "double_bed_capacity": 2,
        "extra_single_bed_capacity": 0,
        "extra_double_bed_capacity": 0,
    }
    
    defaults.update(kwargs)
    
    bed_space_type = frappe.get_doc({
        "doctype": "Bed Space Type",
        **defaults
    })
    bed_space_type.insert(ignore_permissions=True)
    return bed_space_type

def create_test_accommodation_space_type(space_type_name="Test Space Type", **kwargs):
    """Create or get test accommodation space type"""
    if frappe.db.exists("Accommodation Space Type", space_type_name):
        return frappe.get_doc("Accommodation Space Type", space_type_name)
    
    defaults = {
        "space_type": space_type_name,
        "abbreviation": "TST",
        "bed_space_available": 1,
    }
    
    defaults.update(kwargs)
    
    space_type = frappe.get_doc({
        "doctype": "Accommodation Space Type",
        **defaults
    })
    space_type.insert(ignore_permissions=True)
    return space_type

def create_test_accommodation_unit(accommodation, floor_name="Test Floor", **kwargs):
    """Create or create test accommodation unit"""
    unit_name = kwargs.get("unit_name", "Test Unit")
    
    if frappe.db.exists("Accommodation Unit", unit_name):
        return frappe.get_doc("Accommodation Unit", unit_name)
    
    # Create Accommodation Type if it doesn't exist
    accommodation_type_name = "Test Type"
    if not frappe.db.exists("Accommodation Type", accommodation_type_name):
        acc_type = frappe.get_doc({
            "doctype": "Accommodation Type",
            "accommodation_type": accommodation_type_name,
        })
        acc_type.insert(ignore_permissions=True)
    
    # Create test space type if it doesn't exist
    space_type_name = "Test Space Type"
    if not frappe.db.exists("Accommodation Space Type", space_type_name):
        space_type = frappe.get_doc({
            "doctype": "Accommodation Space Type",
            "space_type": space_type_name,
            "abbreviation": "TST",
            "bed_space_available": 1,
        })
        space_type.insert(ignore_permissions=True)
    
    # Create or get Floor - using floor_name as the unique identifier
    # The Floor doctype uses floor_name as its primary key (autoname field)
    if not frappe.db.exists("Floor", floor_name):
        try:
            floor = frappe.get_doc({
                "doctype": "Floor",
                "floor_name": floor_name,
                "floor": 99,  # Floor number
            })
            floor.flags.ignore_validate = True
            floor.flags.ignore_links = True
            floor.insert(ignore_permissions=True)
            frappe.db.commit()  # Ensure floor is committed to DB
        except (frappe.exceptions.DuplicateEntryError, Exception) as e:
            # Floor already exists or other error, just continue
            frappe.clear_messages()
            frappe.db.commit()
    
    # Get the floor number from the created Floor
    floor_record = frappe.db.get_value("Floor", floor_name, ["floor"], as_dict=True)
    floor_num = floor_record.get("floor") if floor_record else 99
    
    defaults = {
        "accommodation": accommodation,
        "accommodation_unit": unit_name,
        "floor_name": floor_name,
        "floor": floor_num,
        "type": accommodation_type_name,
        "space_details": [
            {
                "doctype": "Accommodation Unit Space Type",
                "space_type": space_type_name,
                "total_number": 10,
            }
        ]
    }
    
    defaults.update(kwargs)
    
    unit = frappe.get_doc({
        "doctype": "Accommodation Unit",
        **defaults
    })
    unit.flags.ignore_validate = True
    unit.flags.ignore_links = True
    unit.insert(ignore_permissions=True)
    return unit

def create_test_accommodation_space(accommodation, accommodation_unit, space_type, bed_space_type, **kwargs):
    """Create test accommodation space with beds"""
    space_name = kwargs.get("space_name", "Test Space")
    
    if frappe.db.exists("Accommodation Space", space_name):
        return frappe.get_doc("Accommodation Space", space_name)
    
    # Get accommodation unit to fetch floor_name
    acc_unit = frappe.get_doc("Accommodation Unit", accommodation_unit)
    
    defaults = {
        "accommodation": accommodation,
        "accommodation_unit": accommodation_unit,
        "accommodation_space_type": space_type,
        "bed_space_type": bed_space_type,
        "floor_name": acc_unit.floor_name,  # Set floor_name from accommodation unit
        "bed_space_available": 1,
        "gender": "Male",
        "bed_type": "Single",
    }
    
    defaults.update(kwargs)
    
    space = frappe.get_doc({
        "doctype": "Accommodation Space",
        **defaults
    })
    space.flags.ignore_validate = True
    space.flags.ignore_links = True
    space.insert(ignore_permissions=True)
    return space

def create_test_bed(accommodation_space, bed_id="TEST-BED-001", **kwargs):
    """Create test bed"""
    if frappe.db.exists("Bed", bed_id):
        return frappe.get_doc("Bed", bed_id)
    
    # Get accommodation space to fetch related data
    acc_space = frappe.get_doc("Accommodation Space", accommodation_space)
    
    defaults = {
        "accommodation_space": accommodation_space,
        "accommodation": acc_space.accommodation,
        "accommodation_unit": acc_space.accommodation_unit,
        "accommodation_space_type": acc_space.accommodation_space_type,
        "bed_space_type": acc_space.bed_space_type,
        "status": "Vacant",
        "bed_type": "Single",
        "gender": "Male",
    }
    
    defaults.update(kwargs)
    
    bed = frappe.get_doc({
        "doctype": "Bed",
        **defaults
    })
    bed.flags.ignore_validate = True
    bed.flags.ignore_links = True
    bed.insert(ignore_permissions=True)
    return bed