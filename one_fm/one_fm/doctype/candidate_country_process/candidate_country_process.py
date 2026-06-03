# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CandidateCountryProcess(Document):
    def validate(self):
        today = frappe.utils.getdate()
        rows = self.agency_process_details

        # ── 1. PLANNED DATE: static baseline set once at creation ─────────────
        # Uses dependency graph (before_task) to compute planned dates.
        self._compute_planned_dates(rows)

        # ── 2. LIVE PLAN DATE: dynamic cascade using dependency graph ─────────
        self._compute_live_plan_dates(rows)

        # ── 3. ETA STATUS: planned date vs actual / today ─────────────────────
        for row in rows:
            if row.get("status") == "Skipped":
                row.eta_status = ""
                continue

            planned = frappe.utils.getdate(row.get("planned_date")) if row.get("planned_date") else None
            actual  = frappe.utils.getdate(row.actual_date) if row.actual_date else None

            if not actual:
                if planned and today > planned:
                    row.eta_status = "Late"
                else:
                    row.eta_status = "Still Within Time frame"
            else:
                if planned and actual > planned:
                    row.eta_status = "Late"
                elif planned and actual < planned:
                    row.eta_status = "Completed Early"
                else:
                    row.eta_status = "Completed on time"

        # ── 4. Mirror Live Plan ETA to header field ───────────────────────────
        if rows:
            last = rows[-1]
            if last.get("live_plan_date"):
                self.live_plan_eta = last.live_plan_date
            elif last.get("planned_date"):
                self.live_plan_eta = last.planned_date

    def _compute_planned_dates(self, rows):
        """
        Compute planned_date for each row based on the dependency graph.
        Only fills in rows that don't yet have a planned_date (first save).

        For rows with before_task dependencies:
          - Sequential: starts after the latest before_task planned_date
          - Parallel: starts at the same time as other parallel tasks
                      sharing the same before_task
        """
        if not self.start_date:
            return

        start = frappe.utils.getdate(self.start_date)
        row_map = {r.process_name: r for r in rows}

        for row in rows:
            if row.get("planned_date"):
                continue  # Already set

            if row.duration_in_days is None:
                continue

            anchor = self._get_dependency_anchor(row, row_map, "planned_date", start)
            if anchor:
                row.planned_date = frappe.utils.add_days(anchor, row.duration_in_days)

    def _compute_live_plan_dates(self, rows):
        """
        Compute live_plan_date for each row based on actual completion
        dates of dependencies (falls back to live_plan_date, then planned_date).
        """
        if not self.start_date:
            return

        start = frappe.utils.getdate(self.start_date)
        row_map = {r.process_name: r for r in rows}

        for row in rows:
            if row.get("status") == "Skipped":
                row.live_plan_date = None
                continue

            if row.duration_in_days is None:
                continue

            anchor = self._get_dependency_anchor_live(row, row_map, start)
            if anchor:
                row.live_plan_date = frappe.utils.add_days(anchor, row.duration_in_days)

    def _get_dependency_anchor(self, row, row_map, date_field, default_start):
        """
        Get the anchor date for planned_date computation.

        If before_task is set, returns the MAX of all before_task planned_dates.
        If no before_task, returns default_start for the first task,
        or the previous row's planned_date for sequential flow.
        """
        before_tasks = self._parse_task_list(row.get("before_task"))

        if not before_tasks:
            # First task in the chain — use start_date
            return default_start

        # Get the latest planned_date among all before_tasks
        max_date = None
        for task_name in before_tasks:
            dep_row = row_map.get(task_name)
            if not dep_row:
                continue
            dep_date = frappe.utils.getdate(dep_row.get(date_field)) if dep_row.get(date_field) else None
            if dep_date and (max_date is None or dep_date > max_date):
                max_date = dep_date

        return max_date or default_start

    def _get_dependency_anchor_live(self, row, row_map, default_start):
        """
        Get the anchor date for live_plan_date computation.

        Uses actual_date if available, falls back to live_plan_date,
        then planned_date of dependency tasks.
        For parallel tasks sharing the same before_task, they all start
        from the same anchor (the before_task's completion).
        """
        before_tasks = self._parse_task_list(row.get("before_task"))

        if not before_tasks:
            return default_start

        # Get the latest effective date among all before_tasks
        max_date = None
        for task_name in before_tasks:
            dep_row = row_map.get(task_name)
            if not dep_row:
                continue

            # Skip dependencies that are Skipped
            if dep_row.get("status") == "Skipped":
                continue

            # Prefer actual_date > live_plan_date > planned_date
            dep_date = None
            if dep_row.actual_date:
                dep_date = frappe.utils.getdate(dep_row.actual_date)
            elif dep_row.get("live_plan_date"):
                dep_date = frappe.utils.getdate(dep_row.live_plan_date)
            elif dep_row.get("planned_date"):
                dep_date = frappe.utils.getdate(dep_row.planned_date)

            if dep_date and (max_date is None or dep_date > max_date):
                max_date = dep_date

        return max_date or default_start

    @staticmethod
    def _parse_task_list(task_str):
        """Parse a comma-separated task list into a list of stripped task names."""
        if not task_str:
            return []
        return [t.strip() for t in task_str.split(",") if t.strip()]

    def autoname(self):
        if not self.candidate_name and self.job_applicant:
            self.candidate_name = frappe.db.get_value('Job Applicant', self.job_applicant, 'applicant_name')

        if self.candidate_name and self.job_offer:
            self.name = f"{self.candidate_name} - {self.job_offer}"
        elif self.candidate_name:
            self.name = self.candidate_name
        else:
            from frappe.model.naming import make_autoname
            self.name = make_autoname('CCP-#####')

    def after_insert(self):
        if self.agency_process_details:
            for agency_process_details in self.agency_process_details:
                if agency_process_details.reference_type:
                    self.current_process_id = agency_process_details.name
                    self.db_set('current_process_id', agency_process_details.name)
                    break

    def on_update(self):
        """Auto-create linked DocType records when a step reaches its trigger status."""
        if getattr(self.flags, '_in_auto_create', False):
            return
        self.flags._in_auto_create = True
        try:
            self._auto_create_next_records()
        finally:
            self.flags._in_auto_create = False

    def _auto_create_next_records(self):
        """
        Data-driven trigger logic using before_task / after_task dependencies.

        When a task's status matches its reference_complete_status_value,
        find all tasks whose before_task includes this task and auto-create
        their linked records — but only if ALL of their before_task
        dependencies are also complete.
        """
        rows = self.agency_process_details
        if not rows:
            return

        row_map = {r.process_name: r for r in rows}

        for row in rows:
            # Check if this row is "complete" per its configured status
            if not row.reference_complete_status_value:
                continue
            if row.status != row.reference_complete_status_value:
                continue

            # This task is complete — find tasks that depend on it (after_task)
            after_tasks = self._parse_task_list(row.get("after_task"))
            for target_name in after_tasks:
                target_row = row_map.get(target_name)
                if not target_row or not target_row.reference_type:
                    continue

                # Skip if record already exists
                if target_row.reference_name:
                    continue

                # Check ALL before_task dependencies of the target are complete
                if not self._all_dependencies_met(target_row, row_map):
                    continue

                new_doc = self._create_linked_record(target_row)
                if new_doc:
                    target_row.reference_name = new_doc.name
                    target_row.db_set("reference_name", new_doc.name, update_modified=False)

    def _all_dependencies_met(self, target_row, row_map):
        """
        Check if ALL before_task dependencies of target_row are complete.
        A dependency is "met" when its status matches its reference_complete_status_value,
        or it is Skipped.
        """
        before_tasks = self._parse_task_list(target_row.get("before_task"))
        if not before_tasks:
            return True  # No dependencies — always ready

        for dep_name in before_tasks:
            dep_row = row_map.get(dep_name)
            if not dep_row:
                continue  # Missing dependency row — skip

            # Skipped counts as met
            if dep_row.get("status") == "Skipped":
                continue

            # Check if the dependency has reached its completion status
            if dep_row.reference_complete_status_value:
                if dep_row.status != dep_row.reference_complete_status_value:
                    return False  # This dependency is not yet complete
            else:
                # No completion status configured — check if it has an actual_date
                if not dep_row.actual_date:
                    return False

        return True

    def _create_linked_record(self, row):
        """Create a new record of the linked DocType for this process step."""
        doctype = row.reference_type
        if not doctype:
            return None

        meta = frappe.get_meta(doctype)

        # Skip DocTypes that don't have candidate_country_process link
        if not meta.has_field("candidate_country_process"):
            return None

        # Build the new document with candidate_country_process link
        try:
            new_doc = frappe.new_doc(doctype)
            new_doc.candidate_country_process = self.name

            # Map common fields if they exist on the target DocType
            field_map = {
                "candidate_name": self.candidate_name,
                "passport_number": self.passport_number,
            }
            for field, value in field_map.items():
                if meta.has_field(field) and value:
                    new_doc.set(field, value)

            new_doc.flags.ignore_permissions = True
            new_doc.flags.ignore_mandatory = True
            new_doc.insert(ignore_permissions=True)

            frappe.msgprint(
                f"Auto-created {doctype}: <b>{new_doc.name}</b>",
                indicator="green",
                alert=True,
            )
            return new_doc

        except Exception as e:
            frappe.log_error(
                f"Failed to auto-create {doctype} for {self.name}: {e}",
                "CCP Auto-Create Error"
            )
            return None

    def on_submit(self):
        pass

    def get_workflow(self):
        workflow_list = []
        if self.agency_process_details:
            for workflow in self.agency_process_details:
                if workflow.reference_type and workflow.name == self.current_process_id:
                    if workflow.reference_name:
                        workflow_list.append(frappe.get_doc(workflow.reference_type, workflow.reference_name).as_dict())
                    else:
                        workflow_list.append({"new_doc": True, "doctype": workflow.reference_type})
        return workflow_list


def update_candidate_country_process():
    query = """
        select
            dt.name as dt_name, ccp.name as ccp_name, dt.process_name, dt.reference_type, dt.reference_name,
            dt.reference_complete_status_value, dt.reference_complete_status_field, dt.idx, dt.planned_date
        from
            `tabCandidate Country Process` ccp, `tabCandidate Country Process Details` dt
        where
            ccp.current_process_id=dt.name
    """
    ccp_list = frappe.db.sql(query, as_dict=True)
    today = frappe.utils.getdate()

    for ccp in ccp_list:
        delay = 0
        if ccp.planned_date and today > ccp.planned_date:
            delay = (today - ccp.planned_date).days

        if ccp.reference_type and ccp.ccp_name:
            process_doc = frappe.get_doc(ccp.reference_type, {'candidate_country_process': ccp.ccp_name})
            if process_doc:
                if not ccp.reference_name:
                    frappe.db.set_value('Candidate Country Process Details', ccp.dt_name, 'reference_name', process_doc.name)

                if process_doc.get(ccp.reference_complete_status_field) == ccp.reference_complete_status_value:
                    frappe.db.set_value('Candidate Country Process Details', ccp.dt_name, 'status', 'Approved')
                    frappe.db.set_value('Candidate Country Process Details', ccp.dt_name, 'actual_date', today)

                    ccp_doc = frappe.get_doc('Candidate Country Process', ccp.ccp_name)

                    if len(ccp_doc.agency_process_details) > ccp.idx:
                        for process_list in ccp_doc.agency_process_details:
                            if process_list.idx > ccp.idx and process_list.reference_type:
                                ccp_doc.db_set('current_process_id', process_list.name)
                                break
                    ccp_doc.save(ignore_permissions=True)
