# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class OKRPerformanceProfile(Document):
    
    def update_kr_value(self):
        for each in self.key_results:
            matched_row = self.get_matched_row(each.objective)
            if matched_row:
                each.matched_row = matched_row
            else:
                each.matched_row = None
                each.objective = ""
    
    def get_matched_row(self,obj):
        found = False
        row_id = None
        #Get the row ID from the objectives table and update the key results table with each time it appears, this will enable real time update
        for each in self.objectives:
            if each.objective == obj:
                found = True
                row_id = each.name
        return None if not found else row_id 
        
            
    
    def validate(self):
     self.validate_kr_time_frame_total()
     self.update_kr_value()

    def validate_kr_time_frame_total(self):
        if self.objectives and self.key_results:
            for objective in self.objectives:
                total_days_to_achieve_target = 0
                for key_result in self.key_results:
                    if (key_result.objective == objective.objective) and (type(key_result.target_to_be_achieved_by) in [float, int]):
                        total_days_to_achieve_target += key_result.target_to_be_achieved_by
                if total_days_to_achieve_target > objective.time_frame:
                    frappe.msgprint(_("""Total of Achieve Target by for the objective <b>{0}</b> is greater than the Time Frame""").format(objective.objective))
