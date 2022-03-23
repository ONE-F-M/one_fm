import random
import frappe, html
from frappe.www.contact import send_message

def get_context(context):
    context.twilio_number = frappe.db.sql(f"""
        SELECT * FROM `tabSingles` WHERE doctype='Twilio Setting' AND field='t_number';
        """, as_dict=1)[0].value
    return context

@frappe.whitelist(allow_guest=True)
def get_data():
    """
     GET GENERAL WEBSITE DATA
    """
    context = frappe._dict({})

    # get recent job opening
    context.job_opening = frappe.db.sql("""
        SELECT name, description FROM `tabJob Opening`
        WHERE status='Open' AND publish=1
        ORDER BY modified DESC
        LIMIT 4
        """, as_dict=1)

    # get projects, sites, customers, employeers
    projects = []
    projects.append({'name':'Projects', 'value':frappe.db.count('Project')})
    projects.append({'name':'Sites', 'value':frappe.db.count('Operations Site')})
    projects.append({'name':'Clients', 'value':frappe.db.count('Customer')})
    projects.append({'name':'Employees', 'value':frappe.db.count('Employee', {
        'status':'Active'
    })})
    context.projects = projects
    partners = [i.image for i in
            frappe.db.sql("""
                SELECT image FROM `tabCustomer`
                WHERE image IS NOT NULL;""",
        as_dict=1)]
    try:
        out_sample = random.sample(partners, 12)
    except Exception as e:
        out_sample = random.sample(partners, len(partners))
    context.partners = out_sample

    return context


@frappe.whitelist(allow_guest=True)
def send_contact_email(name, email, subject, message):
    """
     SEND contact form email
    """
    try:
        frappe.sendmail(recipients=['support@one-fm.com'], sender=email,
            subject=subject, message=message)
        # post to frappe contact form processor
        send_message(subject=subject, sender=email,
        message=f"""Name: {name}\nSubject: {subject}\nEmail: {email}\n\n{message}""")
        return True
    except Exception as e:
        frappe.log_error(e)
        return False
