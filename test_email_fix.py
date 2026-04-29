import frappe
from one_fm.events.email_queue import send_email_as_admin

def test_send_email_as_admin():
    # Create a dummy email queue record
    email_queue = frappe.get_doc({
        "doctype": "Email Queue",
        "sender": "test@example.com",
        "subject": "Test Subject",
        "message": "Test Message",
        "status": "Not Sent",
        "recipients": [
            {"recipient": "recipient@example.com"}
        ]
    }).insert(ignore_permissions=True)
    
    frappe.db.commit()
    
    print(f"Created Email Queue: {email_queue.name}")
    
    # Try to send it as admin
    try:
        send_email_as_admin(email_queue.name)
        print("Successfully called send_email_as_admin")
        
        # Check status
        email_queue.reload()
        print(f"Email Queue Status: {email_queue.status}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    test_send_email_as_admin()
