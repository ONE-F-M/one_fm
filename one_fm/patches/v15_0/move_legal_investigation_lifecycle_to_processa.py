import frappe

from one_fm.custom.workflow.workflow import create_workflow_state
from one_fm.grd.processa import retire_workflow

LEGACY_DAMAGE_FLAGS = ("company_damage", "asset_damage", "customer_property_damage", "other_damages")


def execute():
	# The Initiate Legal Investigation process sets every state; Penalty Applied is new.
	retire_workflow("Legal Investigation", "Legal Investigation", ())
	create_workflow_state([{"workflow_state_name": "Penalty Applied", "style": "Danger"}])

	for doctype in ("Legal Investigation", "Legal Investigation Penalty"):
		set_third_party_damage(doctype)


def set_third_party_damage(doctype):
	"""third_party_damage replaces the four legacy damage checks, whose columns stay."""
	flags = [flag for flag in LEGACY_DAMAGE_FLAGS if frappe.db.has_column(doctype, flag)]
	if not flags:
		return

	table = frappe.qb.DocType(doctype)
	condition = None
	for flag in flags:
		condition = (table[flag] == 1) if condition is None else condition | (table[flag] == 1)
	frappe.qb.update(table).set(table.third_party_damage, 1).where(condition).run()
