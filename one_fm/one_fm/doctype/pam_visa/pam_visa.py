# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PAMVisa(Document):
    def validate(self):
        if self.status == 'Rejected' and self.visa_application_rejected==0:
            self.visa_application_rejected = 1

            frappe.get_doc({
                "doctype":"PAM Visa"
            }).insert(ignore_permissions=True)


    def get_applicant_data(self):
        if self.candidate_country_process:
            candidate_country_process_doc = frappe.get_doc("Candidate Country Process", self.candidate_country_process)

            job_applicant_name = frappe.get_value("Job Offer", {"name": candidate_country_process_doc.applicant}, "job_applicant")

            doc = frappe.get_doc("Job Applicant", job_applicant_name)

            self.english_first_name = doc.one_fm_first_name
            self.english_second_name = doc.one_fm_second_name
            self.english_third_name = doc.one_fm_third_name
            self.english_last_name = doc.one_fm_last_name
            self.arabic_first_name = doc.one_fm_first_name_in_arabic
            self.arabic_second_name = doc.one_fm_second_name_in_arabic
            self.arabic_third_name = doc.one_fm_third_name_in_arabic
            self.arabic_last_name = doc.one_fm_last_name_in_arabic

            self.nationality = '***'
            self.marital_status = doc.one_fm_marital_status
            self.gender = doc.one_fm_gender
            self.religion = doc.one_fm_religion
            self.place_of_birth = doc.one_fm_place_of_birth
            self.date_of_birth = doc.one_fm_date_of_birth
            self.practical_qualification = '***'
            self.passport_number = doc.one_fm_passport_number

            self.passport_type = doc.one_fm_passport_type
            self.passport_nationality = doc.one_fm_passport_holder_of
            self.date_of_issuance = doc.one_fm_passport_issued
            self.date_of_expiry = doc.one_fm_passport_expire
            self.passport_issuer = '***'
            self.basic_salary = doc.one_fm_current_salary
            self.salary_type = '***'

            frappe.db.commit()

        return "True"

