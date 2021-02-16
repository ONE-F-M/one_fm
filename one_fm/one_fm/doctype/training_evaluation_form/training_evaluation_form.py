# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.website_generator import WebsiteGenerator
import json
from frappe.utils import cstr

class TrainingEvaluationForm(WebsiteGenerator):
	pass


@frappe.whitelist(allow_guest=True)
def submit_training_feedback(args):
	args = json.loads(args)
	template_name = frappe.get_value("Training Evaluation Form", args['ref'], "training_form_template")
	template_doc = frappe.get_doc("Training Evaluation Form Template", template_name)

	response_doc = frappe.new_doc("Training Evaluation Form Response")
	response_doc.training_evaluation_form = args['ref']
	response_doc.training_event = frappe.get_value("Training Evaluation Form", args['ref'], "training_event")
	response_doc.start_date = args['startTime']
	response_doc.end_date = args['endTime']
	response_doc.additional_comments = args['additional_comments']

	for question in template_doc.questions:
		data = { "question": question.question }
		key = args[cstr(question.idx)]
		data[key] = 1
		response_doc.append("questions", data)

	response_doc.insert()
	response_doc.submit()
	return True