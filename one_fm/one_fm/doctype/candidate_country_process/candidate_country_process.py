# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CandidateCountryProcess(Document):
    def get_candidate_passport_number(self):

        job_applicant_name = frappe.get_value("Job Offer", {"name": self.applicant}, "job_applicant")

        doc = frappe.get_doc("Job Applicant", job_applicant_name)
        return doc.one_fm_passport_number
