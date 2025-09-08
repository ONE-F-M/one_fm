import frappe

def execute():
    factors_data = [
        ("Company Mission & Values (optional addition)", "Alignment with your personal purpose and values"),
        ("Job Stretch & Learning", "Bigger challenges, scope, and learning potential"),
        ("Continuing Growth Rate", "Long-term career advancement and opportunity"),
        ("Work/Life Balance", "Time and flexibility for personal life and well-being"),
        ("Projects & Technology", "A mix of more satisfying and engaging work"),
        ("Manager & Teams", "Working with the right types of people and leaders"),
        ("Compensation", "Total rewards including salary, benefits, and bonuses"),
    ]

    for factors, description in factors_data:
        doc = frappe.get_doc({
            "doctype": "Career Move Factors",
            "factors": factors,
            "description": description
        })
        doc.insert(ignore_permissions=True)