import frappe
import random,json
import requests
from one_fm.api.v1.utils import response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Cache key holding the full filtered pool of quotes fetched once per day by the
# scheduled set_cached_quote(). User-facing endpoints pick randomly from this pool
# so they never call the external zenquotes.io API (which rate-limits with 429s).
QUOTE_POOL_CACHE_KEY = "zenquote_pool"
ZENQUOTES_URL = "https://zenquotes.io/api/quotes?maxLength=200"
FALLBACK_QUOTE = {"quote": "No quote available", "author": "Unknown", "html": ""}


def _get_quote_from_pool():
	"""Return a random quote dict from the daily-cached pool. Never calls the external API.

	Falls back to the legacy single-quote cache, and finally to a static default,
	so a cold cache degrades gracefully instead of hitting (and being throttled by)
	zenquotes.io on every request.
	"""
	pool = frappe.cache().get_value(QUOTE_POOL_CACHE_KEY)
	if pool:
		try:
			quotes = json.loads(pool)
			if quotes:
				return random.choice(quotes)
		except (ValueError, TypeError):
			pass
	return get_cached_quote()


def get_session_with_retries():
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session






@frappe.whitelist()
def fetch_quote(direct_response = False):
    """
        Return a quote from the daily-cached pool (populated by set_cached_quote).

        Serves from cache only — no live call to zenquotes.io — so frequent
        callers (desk popup, face recognition, bug buster) can never trigger the
        external API's rate limiting.
    """
    data = _get_quote_from_pool()
    if direct_response:
        return data
    return response("Success", 200, data)



def get_cached_quote():
    #fetch the cached quote .This is the fallback incase any error occurs while fetching quotes
    quote = frappe.cache().get_value('daily_quote')
    if quote:
        try:
            return json.loads(quote)
        except:
            return {"quote": "No quote available", "author": "Unknown", "html": ""}
    return {"quote": "No quote available", "author": "Unknown", "html": ""}
    


def set_cached_quote():
    # Scheduled daily: fetch quotes once and cache the full filtered pool so all
    # user-facing endpoints can serve from cache without hitting the external API.
    # This is the ONLY place that calls zenquotes.io.
    try:
        keyword = fetch_keyword().lower()
        session = get_session_with_retries()
        res = session.get(ZENQUOTES_URL, timeout=10)

        if res.status_code != 200:
            # Transient (e.g. 429). Keep the previous cache and log a warning
            # instead of an Error Log — this is expected and not actionable.
            frappe.logger("zenquotes").warning(
                f"zenquotes.io returned {res.status_code}; keeping previous cached pool"
            )
            return

        json_response = json.loads(res.text)

        # Filter quotes that match the keyword; fall back to all quotes if none match
        matching_quotes = [q for q in json_response if keyword in q.get('q', '').lower() or keyword in q.get('a', '').lower()]
        if not matching_quotes:
            matching_quotes = json_response

        pool = [
            {'quote': q.get('q', ''), 'author': q.get('a', 'Unknown'), 'html': q.get('h', '')}
            for q in matching_quotes
        ]
        if pool:
            frappe.cache().set_value(QUOTE_POOL_CACHE_KEY, json.dumps(pool))
            # Keep the legacy single-quote key populated for backward compatibility
            frappe.cache().set_value('daily_quote', json.dumps(random.choice(pool)))

    except Exception:
        frappe.logger("zenquotes").warning("Error setting quote cache", exc_info=True)
        return
    
    
    
    
    


def fetch_keyword():
    #Fetch the appropriate keyword to be used in generating the quotes. 
    # The full list of available keywords can be found in the Zenquotes documentations
    keywords = frappe.get_all("Zenquote Keyword Category",{'parent':'ONEFM General Setting'},['keyword'])
    if not keywords:
        return 'inspiration'
    #randomly return a choice based on the approved keywords
    return random.choice(keywords).keyword
    
@frappe.whitelist()
def run_quotes():
    # Serve from the daily-cached pool only. The desk popup (desk.js) calls this on
    # every load and hourly per user, so it must never hit zenquotes.io live.
    return {'results': _get_quote_from_pool()}