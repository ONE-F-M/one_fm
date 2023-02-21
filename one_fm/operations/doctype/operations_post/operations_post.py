# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc
from frappe.utils import cstr, getdate, add_to_date, date_diff, now
import pandas as pd
from one_fm.operations.doctype.contracts.contracts import get_active_contracts_for_project
from frappe.model.naming import NamingSeries

class OperationsPost(Document):
    def after_insert(self):
        create_post_schedule_for_operations_post(self)

    def validate(self):
        if not self.post_name:
            frappe.throw("Post Name cannot be empty.")

        if not self.gender:
            frappe.throw("Gender cannot be empty.")

        if not self.site_shift:
            frappe.throw("Shift cannot be empty.")

        if(frappe.db.get_value('Operations Role', self.post_template, 'shift') != self.site_shift):
            frappe.throw(f"Operations Role ({self.post_template}) does not belong to selected shift ({self.site_shift})")

        self.validate_operations_role_status()

    def validate_operations_role_status(self):
        if self.status == 'Active' and self.post_template \
            and frappe.db.get_value('Operations Role', self.post_template, 'is_active') != 1:
            frappe.throw(_("The Operations Role <br/>'<b>{0}</b>' selected in the Post '<b>{1}</b>' is <b>Inactive</b>. <br/> To make the Post atcive first make the Role active".format(self.post_template, self.name)))

    def on_update(self):
        self.validate_name()

    def validate_name(self):
        condition = self.post_name+"-"+self.gender+"|"+self.site_shift
        if condition != self.name:
            rename_doc(self.doctype, self.name, condition, force=True)

    def on_update(self):
        if self.status == "Active":
            check_list = frappe.db.get_list("Post Schedule", filters={"post":self.name, "date": [">", getdate()]})
            if len(check_list) < 1 :
                create_post_schedule_for_operations_post(self)
        elif self.status == "Inactive":
            frappe.enqueue(delete_schedule, doc=self, is_async=True, queue="long")

def delete_schedule(doc):
    check_list = frappe.db.get_list("Post Schedule", filters={"post": doc.name, "date": [">", getdate()]})
    for schedule in check_list:
        frappe.get_doc("Post Schedule", schedule.name).delete()
    frappe.db.commit()

def create_post_schedule_for_operations_post(operations_post):
    
    if type(operations_post) == str:
        operations_post = frappe.get_doc("Operations Post",operations_post)
    contracts = get_active_contracts_for_project(operations_post.project)
    
    if contracts:
        
        if contracts.end_date >= getdate():
            try:
                owner = frappe.session.user
                creation = now()
                query = """
                    Insert Into
                        `tabPost Schedule`
                        (
                            `name`, `post`, `operations_role`, `post_abbrv`, `shift`, `site`, `project`, `date`, `post_status`,
                            `owner`, `modified_by`, `creation`, `modified`, `paid`, `unpaid`
                        )
                    Values
                """
                post_abbrv = frappe.db.get_value("Operations Role", operations_post.post_template, ["post_abbrv"])
                naming_series = NamingSeries('PS-')
                ps_name_idx = previous_series = naming_series.get_current_value()
                today = getdate()
                start_date = today if contracts.start_date < today else contracts.start_date
                for date in	pd.date_range(start=start_date, end=contracts.end_date):
                    if not frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": operations_post.name}):
                        ps_name_idx += 1
                        ps_name = 'PS-'+str(ps_name_idx).zfill(5)
                        query += f"""
                            (
                                "{ps_name}", "{operations_post.name}", "{operations_post.post_template}", "{post_abbrv}",
                                "{operations_post.site_shift}", "{operations_post.site}", "{operations_post.project}",
                                '{cstr(date.date())}', 'Planned', "{owner}", "{owner}", "{creation}", "{creation}", '0', '0'
                            ),"""
                if previous_series == ps_name_idx:
                    frappe.msgprint(_("Post is already scheduled."))
                else:
                    
                    frappe.db.sql(query[:-1], values=[], as_dict=1)
                    frappe.db.commit()
                    naming_series.update_counter(ps_name_idx)
                    frappe.msgprint(_("Post is scheduled as Planned."))
            except Exception as e:
                frappe.db.rollback()
                frappe.log_error('Post Schedule from Operations Post', e)
                frappe.msgprint(_("Error log is added."), alert=True, indicator='orange')
                operations_post.reload()
        else:
            frappe.msgprint(_("End date of the contract referenced in by the project is less than today."))
    else:
        frappe.msgprint(_("No active contract found for the project referenced."))
