import frappe

from one_fm.api.v2.zenquotes import set_cached_quote


def execute():
	"""Warm the zenquote cache pool so user-facing endpoints have quotes to serve
	immediately, instead of waiting for the daily scheduler's first run."""
	set_cached_quote()
