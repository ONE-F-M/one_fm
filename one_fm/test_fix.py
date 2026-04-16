import frappe
from one_fm.one_fm.utils import leave_application_on_cancel
from frappe.utils import getdate

class MockDoc:
    def __init__(self, from_date, employee, leave_type=None):
        self.from_date = from_date
        self.employee = employee
        self.leave_type = leave_type

def test_leave_application_on_cancel():
    # Mock doc with from_date as date object
    doc = MockDoc(getdate("2023-01-01"), "EMP-001")
    
    try:
        # This should not raise TypeError
        leave_application_on_cancel(doc, "on_cancel")
        print("Test passed: No TypeError raised for date object")
    except TypeError as e:
        print(f"Test failed: TypeError raised for date object: {e}")
    except Exception as e:
        # It might fail because EMP-001 doesn't exist, but we only care about TypeError
        if "TypeError" in str(e):
            print(f"Test failed: TypeError raised: {e}")
        else:
            print(f"Test passed: No TypeError raised (other error: {e})")

    # Mock doc with from_date as string
    doc_str = MockDoc("2023-01-01", "EMP-001")
    try:
        leave_application_on_cancel(doc_str, "on_cancel")
        print("Test passed: No TypeError raised for string")
    except TypeError as e:
        print(f"Test failed: TypeError raised for string: {e}")
    except Exception as e:
        if "TypeError" in str(e):
            print(f"Test failed: TypeError raised: {e}")
        else:
            print(f"Test passed: No TypeError raised (other error: {e})")

if __name__ == "__main__":
    frappe.connect(site="onefm")
    test_leave_application_on_cancel()
