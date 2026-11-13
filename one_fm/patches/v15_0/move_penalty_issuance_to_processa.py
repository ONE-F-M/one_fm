import frappe
from frappe.permissions import add_permission, update_permission_property

from one_fm.patches.v15_0.move_legal_investigation_lifecycle_to_processa import set_third_party_damage

# The roles that issue penalties. The Initiate Penalty Issuance process runs its scripts as
# the issuer, and those scripts create the Legal Investigation, HR Enquiry and Penalty.
ISSUER_ROLES = ("Penalty Issuer", "Shift Supervisor", "Site Supervisor", "HR User")


def execute():
	set_third_party_damage("Penalty Issuance")
	allow_issuers_to_create("Legal Investigation", "Penalty")


def allow_issuers_to_create(*doctypes):
	"""Create only: issuers still see no Legal Investigation or Penalty they had no access to."""
	for doctype in doctypes:
		for role in ISSUER_ROLES:
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}):
				update_permission_property(doctype, role, 0, "create", 1)
			else:
				add_permission(doctype, role, 0, "create")
