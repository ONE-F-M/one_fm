# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, comma_and, cstr, getdate, nowdate

class ApplicantLead(Document):
	def validate(self):
		self._prev = frappe._dict({
			"contact_date": frappe.db.get_value("Lead", self.name, "contact_date") if (not cint(self.is_new())) else None,
			"ends_on": frappe.db.get_value("Lead", self.name, "ends_on") if (not cint(self.is_new())) else None,
			"contact_by": frappe.db.get_value("Lead", self.name, "contact_by") if (not cint(self.is_new())) else None,
		})
		self.check_email_id_is_unique()
		self.check_mobile_no_is_unique()
		if self.contact_date and getdate(self.contact_date) < getdate(nowdate()):
			frappe.throw(_("Next Contact Date cannot be in the past"))

		if (self.ends_on and self.contact_date and (getdate(self.ends_on) < getdate(self.contact_date))):
			frappe.throw(_("Ends On date cannot be before Next Contact Date."))

	def check_email_id_is_unique(self):
		if self.email_id:
			# validate email is unique
			duplicate_leads = frappe.get_all("Applicant Lead", filters={"email_id": self.email_id, "name": ["!=", self.name]})
			duplicate_leads = [lead.name for lead in duplicate_leads]

			if duplicate_leads:
				frappe.throw(_("Email Address must be unique, already exists for {0}")
				.format(comma_and(duplicate_leads)), frappe.DuplicateEntryError)

	def check_mobile_no_is_unique(self):
		if self.mobile_no:
			# validate email is unique
			duplicate_leads = frappe.get_all("Applicant Lead", filters={"mobile_no": self.mobile_no, "name": ["!=", self.name]})
			duplicate_leads = [lead.name for lead in duplicate_leads]

			if duplicate_leads:
				frappe.throw(_("Mobile must be unique, already exists for {0}")
				.format(comma_and(duplicate_leads)), frappe.DuplicateEntryError)

	def on_update(self):
		if cstr(self.contact_by) != cstr(self._prev.contact_by) or \
				cstr(self.contact_date) != cstr(self._prev.contact_date) or \
				(hasattr(self, "ends_on") and cstr(self.ends_on) != cstr(self._prev.ends_on)):

			self.delete_events()
			opts = {
				"owner": self.lead_owner,
				"starts_on": self.contact_date,
				"ends_on": self.ends_on or "",
				"subject": ('Contact ' + cstr(self.applicant_name)),
				"description": ('Contact ' + cstr(self.applicant_name)) + (self.contact_by and ('. By : ' + cstr(self.contact_by)) or '')
			}
			self._add_calendar_event(opts)

	def delete_events(self):
		participations = frappe.get_all("Event Participants", filters={"reference_doctype": self.doctype, "reference_docname": self.name,
			"parenttype": "Event"}, fields=["name", "parent"])

		if participations:
			for participation in participations:
				total_participants = frappe.get_all("Event Participants", filters={"parenttype": "Event", "parent": participation.parent})
				if len(total_participants) <= 1:
					frappe.db.sql("delete from `tabEvent` where name='%s'" % participation.parent)
				frappe.db.sql("delete from `tabEvent Participants` where name='%s'" % participation.name)

	def _add_calendar_event(self, opts):
		opts = frappe._dict(opts)

		if self.contact_date:
			event = frappe.get_doc({
				"doctype": "Event",
				"owner": opts.owner or self.lead_owner,
				"subject": opts.subject,
				"description": opts.description,
				"starts_on":  self.contact_date,
				"ends_on": opts.ends_on,
				"event_type": "Private"
			})

			event.append('event_participants', {
				"reference_doctype": self.doctype,
				"reference_docname": self.name
				}
			)

			event.insert(ignore_permissions=True)

			if frappe.db.exists("User", self.contact_by):
				frappe.share.add("Event", event.name, self.contact_by, flags={"ignore_share_permission": True})

	def on_trash(self):
		self.delete_events()

@frappe.whitelist()
def make_job_applicant(source_name, target_doc=None):
	target_doc = get_mapped_doc("Applicant Lead", source_name,
	{"Applicant Lead": {
		"doctype": "Job Applicant",
		"field_map": {
			"applicant_name": "one_fm_first_name",
			"email_id": "one_fm_email_id",
			"mobile_no": "one_fm_contact_number",
			"nationality": "one_fm_nationality",
			"gender": "one_fm_gender"
		}
	}}, target_doc)

	return target_doc
