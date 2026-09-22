"""WI-002599: create the passport and date-of-birth fields on Job Offer.

This app has no blanket "sync every custom field on migrate", so a new field needs its own
patch - the same shape as add_currency_exchange_settings_custom_fields and the rest.

create_custom_fields is idempotent and updates a field that already exists, so passing the
whole Job Offer set is safe and keeps this from drifting out of step with the module.

Ordered before backfill_job_offer_passport_details in patches.txt: the columns have to
exist before anything can be written into them.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.job_offer import get_job_offer_custom_fields


def execute():
	create_custom_fields(get_job_offer_custom_fields())
