import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.typing_validations import transform_parameter_types
from one_fm.api.v1.resignation import (
    create_resignation,
    extend_resignation,
    withdraw_resignation,
    get_resignation_by_name,
)

class TestEmployeeResignation(FrappeTestCase):
    def setUp(self):
        # Create a dummy employee to act as our primary user
        if not frappe.db.exists("Employee", "HR-EMP-TEST-99"):
            doc = frappe.get_doc({
                "doctype": "Employee",
                "name": "HR-EMP-TEST-99",
                "employee": "HR-EMP-TEST-99",
                "first_name": "Test Resignation",
                "status": "Active"
            })
            doc.flags.ignore_mandatory = True
            doc.insert()

    def test_create_resignation_invalid_attachment(self):
        # Testing invalid base64 attachment parsing
        with self.assertRaises(frappe.ValidationError):
            create_resignation(
                employee_id="HR-EMP-TEST-99",
                resignation_initiation_date="2026-04-27",
                relieving_date="2026-05-27",
                attachment={
                    "attachment_name": "invalid_attachment.png",
                    "attachment": "not_a_valid_base64_string"
                }
            )


class TestResignationParamTypes(FrappeTestCase):
    def test_extend_resignation_accepts_attachment_object(self):
        # Reverting attachment's type hint to `str` makes this raise FrappeTypeError
        _args, kwargs = transform_parameter_types(
            extend_resignation, (), {"attachment": {"attachment_name": "a.png", "attachment": "abc"}}
        )
        self.assertEqual(kwargs["attachment"], {"attachment_name": "a.png", "attachment": "abc"})

    def test_withdraw_resignation_accepts_attachment_object(self):
        _args, kwargs = transform_parameter_types(
            withdraw_resignation, (), {"attachment": {"attachment_name": "a.png", "attachment": "abc"}}
        )
        self.assertEqual(kwargs["attachment"], {"attachment_name": "a.png", "attachment": "abc"})

    def test_get_resignation_by_name_requires_id(self):
        with self.assertRaises(frappe.ValidationError):
            get_resignation_by_name()


class TestGetResignationByName(FrappeTestCase):
    def setUp(self):
        self.owner_user = _make_user("test-grbn-owner@example.com", "GRBN Owner")
        owner_employee = _make_employee("GRBN-Owner", self.owner_user)
        self.owner_resignation = _make_resignation(owner_employee)

        self.other_user = _make_user("test-grbn-other@example.com", "GRBN Other")
        _make_employee("GRBN-Other", self.other_user)

    def test_owner_gets_their_own_record(self):
        with self.set_user(self.owner_user):
            record = get_resignation_by_name(resignation_id=self.owner_resignation)
        self.assertEqual(record["name"], self.owner_resignation)

    def test_other_employee_cannot_read_it(self):
        # Employee Resignation grants role "Employee" blanket read access, so this
        # only fails if get_resignation_by_name filters by the caller's own employee
        with self.set_user(self.other_user):
            with self.assertRaises(frappe.DoesNotExistError):
                get_resignation_by_name(resignation_id=self.owner_resignation)


def _make_user(email, first_name):
    if frappe.db.exists("User", email):
        return email
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "send_welcome_email": 0
    })
    user.insert()
    return user.name


def _make_employee(name_suffix, user_id):
    existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
    if existing:
        return existing

    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
    company_abbr = frappe.get_cached_value("Company", company, "abbr") or company

    department = f"Test Department - {company_abbr}"
    if not frappe.db.exists("Department", department):
        frappe.get_doc({
            "doctype": "Department",
            "department_name": "Test Department",
            "department_code": "TEST-GRBN-DEPT",
            "company": company
        }).insert()

    project = "Test GRBN Project"
    if not frappe.db.exists("Project", project):
        frappe.get_doc({"doctype": "Project", "project_name": project, "company": company}).insert()

    designation = "Test GRBN Designation"
    if not frappe.db.exists("Designation", designation):
        frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert()

    emp = frappe.get_doc({
        "doctype": "Employee",
        "employee_name": f"Test Employee {name_suffix}",
        "first_name": "Test",
        "last_name": name_suffix,
        "gender": "Male",
        "date_of_birth": "1990-01-01",
        "date_of_joining": "2020-01-01",
        "status": "Active",
        "company": company,
        "department": department,
        "project": project,
        "designation": designation,
        "one_fm_basic_salary": 1000,
        "one_fm_first_name_in_arabic": "تيست",
        "one_fm_last_name_in_arabic": "موظف",
        "user_id": user_id,
    })
    emp.insert()
    return emp.name


def _make_resignation(employee):
    doc = frappe.get_doc({
        "doctype": "Employee Resignation",
        "employee": employee,
        "resignation_initiation_date": frappe.utils.today(),
        "relieving_date": frappe.utils.add_days(frappe.utils.today(), 30),
        "resignation_letter": "/files/test_letter.pdf",
    }).insert()
    return doc.name
