from __future__ import unicode_literals
import frappe
from one_fm.one_fm.utils import create_role_if_not_exists

def execute():
	create_role_if_not_exists(['ERF Approver', 'Unplanned ERF Approver'])
