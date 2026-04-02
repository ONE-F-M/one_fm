# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
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
from one_fm.api.v1.utils import response
from one_fm.operations.report.roster_projection_view.roster_projection_view import execute as report_execute
from one_fm.operations.doctype.contracts.contracts import create_post_schedules

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

        # if(frappe.db.get_value('Operations Role', self.post_template, 'shift') != self.site_shift):
        #     frappe.throw(f"Operations Role ({self.post_template}) does not belong to selected shift ({self.site_shift})")

        self.validate_operations_role_status()
        # check if operations site inactive
        if (self.status=='Active' and frappe.db.exists("Operations Site", {'name':self.site, 'status':'Inactive'})):
            frappe.throw(f"You cannot make this post active because Operations Site '{self.site}' is Inactive.")

        self.update_post_activation_date()

    def validate_operations_role_status(self):
        if self.status == 'Active' and self.post_template \
            and frappe.db.get_value('Operations Role', self.post_template, 'status') != 'Active':
            frappe.throw(_("The Operations Role <br/>'<b>{0}</b>' selected in the Post '<b>{1}</b>' is <b>Inactive</b>. <br/> To make the Post atcive first make the Role active".format(self.post_template, self.name)))

    def update_post_activation_date(self):
        if not self.is_new() and self.has_value_changed("status"):
            old_status = self.get_doc_before_save().status
            if old_status == "Active" and self.status == "Inactive":
                if self.start_date or self.end_date:
                    self.append("operations_post_activation", {
                        "operations_post_start_date": self.start_date,
                        "operations_post_end_date": self.end_date
                    })
                    self.start_date = None
                    self.end_date = None

    def on_update(self):
        self.validate_name()
        if self.has_value_changed("status"):
            if self.status == "Active":
                check_list = frappe.db.get_list(
                    "Post Schedule",
                    filters={
                        "post":self.name, "date": [">", getdate()]
                    }
                )
                if not check_list:
                    create_post_schedule_for_operations_post(self)
            elif self.status == "Inactive":
                delete_schedule(self)

    def validate_name(self):
        condition = self.post_name+"-"+self.gender+"|"+self.site_shift
        if condition != self.name:
            rename_doc(doctype=self.doctype, old=self.name, new=condition, force=True, doc=self)

def delete_schedule(doc):
    frappe.db.sql(f"""
        DELETE FROM `tabPost Schedule` WHERE post="{doc.name}" AND date>'{getdate()}'
    """)

def create_post_schedule_for_operations_post(operations_post):
    contracts = get_active_contracts_for_project(operations_post.project)
    if contracts:
        if contracts.end_date >= getdate():
            today = getdate()
            start_date = today if contracts.start_date < today else contracts.start_date
            sale_item = frappe.db.get_value("Operations Role", operations_post.post_template, "sale_item")
            contract_item = frappe.db.get_value("Contract Items Operation", {
                "parent": contracts.name,
                "item_code": sale_item
            }, ["select_specific_days", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], as_dict=1)

            selected_days = None
            if contract_item and contract_item.select_specific_days:
                day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                selected_days = {i for i, f in enumerate(day_fields) if contract_item.get(f)}
            exists_schedule_in_between = False

            if frappe.db.exists("Post Schedule", {"date": ['between', (start_date, contracts.end_date)], "post": operations_post.name}):
                exists_schedule_in_between = True

                frappe.enqueue(queue_create_post_schedule_for_operations_post, operations_post=operations_post, contracts=contracts, exists_schedule_in_between=exists_schedule_in_between, start_date=start_date, selected_days=selected_days, is_async=True, queue="long")
            else:
                queue_create_post_schedule_for_operations_post(operations_post, contracts, exists_schedule_in_between, start_date, selected_days)
        else:
            frappe.msgprint(_("End date of the contract referenced in by the project is less than today."))
    else:
        frappe.msgprint(_("No active contract found for the project referenced."))

def queue_create_post_schedule_for_operations_post(operations_post, contracts, exists_schedule_in_between, start_date, selected_days=None):
    try:
        owner = frappe.session.user
        creation = now()
        query = """
            Insert Into
                `tabPost Schedule`
                (
                    `name`, `post`, `operations_role`, `post_abbrv`, `shift`, `site`, `project`, `date`, `post_status`,
                    `owner`, `modified_by`, `creation`, `modified`, `paid`
                )
            Values
        """
        post_abbrv = frappe.db.get_value("Operations Role", operations_post.post_template, ["post_abbrv"])
        naming_series = NamingSeries('PS-')
        ps_name_idx = previous_series = naming_series.get_current_value()

        #The previous series value from frappe is wrong in some cases

        for date in	pd.date_range(start=start_date, end=contracts.end_date):
            if selected_days is not None and date.weekday() not in selected_days:
                continue

            date_string = frappe.utils.get_date_str(date.date())
            doc_id_template = f"{operations_post.name}_{date_string}"
            schedule_exists = False
            if exists_schedule_in_between:
                if frappe.db.exists("Post Schedule", {"date": cstr(date.date()),'operations_role': operations_post.post_template, "post": operations_post.name}):
                    schedule_exists = True
            if not schedule_exists:
                ps_name_idx += 1

                query += f"""
                    (
                        "{doc_id_template}", "{operations_post.name}", "{operations_post.post_template}", "{post_abbrv}",
                        "{operations_post.site_shift}", "{operations_post.site}", "{operations_post.project}",
                        '{cstr(date.date())}', 'Planned', "{owner}", "{owner}", "{creation}", "{creation}", '0'
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
        frappe.log_error(message=str(e), title='Post Schedule from Operations Post')
        frappe.msgprint(_("Error log is added."), alert=True, indicator='orange')
        operations_post.reload()

@frappe.whitelist()
def create_new_schedule_for_project(proj):
    # Generate new post schedules for single project that have been generated by the roster projection view report
    try:
        existing_proj = frappe.db.exists("Project",proj)
        if existing_proj:
            contract_items = frappe.db.sql("""
                SELECT ci.item_code
                FROM `tabContract Item` ci
                INNER JOIN `tabContracts` c ON ci.parent = c.name
                WHERE c.project = %s
                    AND c.workflow_state = 'Active'
                    AND (ci.item_type IS NULL OR ci.item_type != 'Items')
            """, (existing_proj,), as_dict=1)

            item_codes = [obj.item_code for obj in contract_items]
            if not item_codes:
                return response("No active contract items found for the specified project", {}, True, 200)

            operations_role = frappe.db.get_list(
                "Operations Role",
                filters={
                    "project": existing_proj,
                    "status": "Active",
                    "sale_item": ["IN", item_codes],
                },
                pluck="name",
            )

            all_operations_post = frappe.get_all(
                "Operations Post",
                {"project": existing_proj, "post_template": ["IN", operations_role], "status": "Active"},
            )
            all_operations_post_ = [frappe.get_doc("Operations Post", i.name) for i in all_operations_post]

            frappe.enqueue(create_post_schedules, operations_posts=all_operations_post_, queue="long",job_name = 'Create Post Schedules')
            return response("Post Creation Scheduled Sucessfully",{}, True, 200)
    except:
        frappe.log_error(title="Post Schedule Creation Error", message=frappe.get_traceback())