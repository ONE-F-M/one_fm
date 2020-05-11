# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class OKRPerformanceProfile(Document):
	def validate(self):
		self.validate_kr_time_frame_total()

	def validate_kr_time_frame_total(self):
		if self.objectives and self.key_results:
			for objective in self.objectives:
				total_days_to_achieve_target = 0
				for key_result in self.key_results:
					if key_result.objective == objective.objective:
						total_days_to_achieve_target += key_result.target_to_be_achieved_by
				if total_days_to_achieve_target > objective.time_frame:
					frappe.msgprint(_("""Total of Achieve Target by for the objective <b>{0}</b> is greater than the Time Frame""").format(objective.objective))
