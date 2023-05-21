import frappe 
from frappe.email.email_body import  get_email

def get_outgoing_support_email(doc):
    if doc.reference_doctype == "HD Ticket":
        email_acc = frappe.get_all("Email Account",{'default_helpdesk_outgoing_email_account':1},['email_id','name'])
        if email_acc:
            return email_acc[0]
        return False

def get_subject(doc):
    ticket_subject = frappe.db.get_value("HD Ticket",doc.reference_name,'subject')
    new_subject = f"Re: {ticket_subject} {doc.reference_name}"
    return new_subject



def prepare_email_content(self):
    sender_ = get_outgoing_support_email(self)
    self.email_sender = sender_.get('email_id') if sender_ else self.sender
    mail = get_email(
        recipients=self.final_recipients(),
        sender=self.email_sender,
        subject=self.subject if self.reference_doctype !='HD Ticket' else get_subject(self),
        formatted=self.email_html_content(),
        text_content=self.email_text_content(),
        attachments=self._attachments,
        reply_to=self.reply_to,
        cc=self.final_cc(),
        bcc=self.bcc,
        email_account=self.get_outgoing_email_account(),
        expose_recipients=self.expose_recipients,
        inline_images=self.inline_images,
        header=self.header,
    )

    mail.set_message_id(self.message_id, self.is_notification)
    if self.read_receipt:
        mail.msg_root["Disposition-Notification-To"] = self.sender
    if self.in_reply_to:
        mail.set_in_reply_to(self.in_reply_to)
    return mail



    

