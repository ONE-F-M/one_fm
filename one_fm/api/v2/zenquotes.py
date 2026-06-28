import frappe
import random,json
import requests
from one_fm.api.v1.utils import response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
        Fetch a quote from zenquotes.io based on configured keywords
        
    """
    try:
        keyword = fetch_keyword().lower()
        base_url = "https://zenquotes.io/api/quotes?maxLength=200"
        
        session = get_session_with_retries()
        res = session.get(base_url, timeout=10)
        
        if res.status_code == 200:
            json_response = json.loads(res.text)
            
            # Filter quotes that match the keyword
            matching_quotes = [q for q in json_response if keyword.lower() in q.get('q', '').lower() or keyword.lower() in q.get('a', '').lower()]
            
            # If no keyword matches found, use all quotes
            if not matching_quotes:
                matching_quotes = json_response
            
            if matching_quotes and len(matching_quotes) > 0:
                selected_quote = random.choice(matching_quotes)
                data = {
                    'quote': selected_quote.get('q', ''), 
                    'author': selected_quote.get('a', 'Unknown'),
                    'html': selected_quote.get('h', '')
                }
                if not direct_response:
                    return response("Success", 200, data)
                else:
                    return data
            else:
                return get_cached_quote()
    except Exception as error:
        frappe.log_error(message=frappe.get_traceback(), title="Error fetching Quote")
        return response("Internal Server Error", 500, None, error)
        
    


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
    #Set a daily quote in cache everyday, with keyword filtering
    base_url = "https://zenquotes.io/api/quotes?maxLength=200"
    try:
        keyword = fetch_keyword().lower()
        session = get_session_with_retries()
        res = session.get(base_url, timeout=10)
        
        if res.status_code == 200:
            json_response = json.loads(res.text)
            
            # Filter quotes that match the keyword
            matching_quotes = [q for q in json_response if keyword.lower() in q.get('q', '').lower() or keyword.lower() in q.get('a', '').lower()]
            
            # If no keyword matches found, use all quotes
            if not matching_quotes:
                matching_quotes = json_response
            
            if matching_quotes and len(matching_quotes) > 0:
                selected_quote = random.choice(matching_quotes)
                quote_dict = json.dumps({
                    'quote': selected_quote.get('q', ''), 
                    'author': selected_quote.get('a', 'Unknown'),
                    'html': selected_quote.get('h', '')
                })
                frappe.cache().set_value('daily_quote', quote_dict)
                return
            
    except Exception as error:
        frappe.log_error(message=frappe.get_traceback(), title="Error Setting Quote in cache")
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
    try:
        base_url = "https://zenquotes.io/api/quotes?maxLength=200"
        keyword = fetch_keyword().lower()
        
        session = get_session_with_retries()
        res = session.get(base_url, timeout=10)
        
        if res.status_code == 200:
            json_response = json.loads(res.text)
            
            # Filter quotes that match the keyword
            matching_quotes = [q for q in json_response if keyword.lower() in q.get('q', '').lower() or keyword.lower() in q.get('a', '').lower()]
            
            # If no keyword matches found, use all quotes
            if not matching_quotes:
                matching_quotes = json_response
            
            if matching_quotes and len(matching_quotes) > 0:
                selected_quote = random.choice(matching_quotes)
                data = {
                    'quote': selected_quote.get('q', ''),
                    'author': selected_quote.get('a', 'Unknown'),
                    'html': selected_quote.get('h', '')
                }
                return {'results': data}
            else:
                return {'results': {'quote': 'No quotes available', 'author': 'Unknown', 'html': ''}}
        else:
            frappe.log_error(message=res.text, title="Error fetching Quote")
            return {'results': {'quote': 'Error fetching quotes', 'author': 'Unknown', 'html': ''}}
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error fetching Quote")
        return {'results': {'quote': 'Error fetching quotes', 'author': 'Unknown', 'html': ''}}