import frappe

@frappe.whitelist()
def sendemail(recipients, subject, header=None, message=None,
        content=None, reference_name=None, reference_doctype=None,
        sender=None, cc=None , attachments=None, delay=None):
    logo = "https://one-fm.com/files/ONEFM_Identity.png"

    frappe.sendmail(template = "default_email",
                    recipients=recipients,
                    sender= sender,
                    cc=cc,
                    reference_name= reference_name,
                    reference_doctype = reference_doctype,
                    subject=subject,
                    args=dict(
                        header=header[0] if header else "",
                        subject=subject,
                        message=message,
                        content=content,
                        logo=logo
                    ),
                    attachments = attachments,
                    delayed=delay)
