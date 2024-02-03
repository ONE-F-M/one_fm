import frappe
import random,json
import requests
from one_fm.api.v1.utils import response



@frappe.whitelist()
def fetch_quote(direct_response = False):
    """
        Fetch a quote from zenquotes.io 
        
    """
    base_url = "https://zenquotes.io/api/quotes/"
    keyword = fetch_keyword().lower()
    api_key = fetch_key()
    url = base_url+api_key+"&?keyword={}".format(keyword)
    try:
        res = requests.get(url)
        if res.status_code == 200:
           
            json_response = json.loads(res.text)
            #Check if the response contains an author tag, this authenticates that a quote was returned and not an error
            if json_response[0].get('a'):
                data = {
                        'quote':json_response[0].get('q'), 
                        'author':json_response[0].get('a'),
                        'html':json_response[0].get('h')
                                                }
                if not direct_response:
                    return response("Success",200,data)
                else:
                    return (data)
            else:
                return get_cached_quote()
    except Exception as error:
        frappe.log_error(frappe.get_traceback(),"Error fetching Quote")
        return response("Internal Server Error", 500, None, error)
        
    


def get_cached_quote():
    #fetch the cached quote .This is the fallback incase any error occurs while fetching quotes
    quote = frappe.cache().get_value('daily_quote')
    return json.loads(quote)
    


def set_cached_quote():
    #Set a daily quote in cache everyday, 
    base_url = "https://zenquotes.io/api/quotes/"
    keyword = 'inspiration'
    api_key = fetch_key()
    url = base_url+api_key+"&?keyword={}".format(keyword)
    try:
        res = requests.get(url)
        if res.status_code == 200:
            json_response = json.loads(res.text)
            #Check if the response contains an author tag, this authenticates that a quote was returned and not an error
            if json_response[0].get('a'):
                quote_dict = json.dumps({'quote':json_response[0].get('q'), 
                                            'author':json_response[0].get('a'),
                                               'html':json_response[0].get('h')
                                               })
                frappe.cache().set_value('daily_quote',quote_dict)
                return
            
    except Exception as error:
        frappe.log_error(frappe.get_traceback(),"Error Setting Quote in cache")
        return response("Internal Server Error", 500, None, error)
    
    
    
    
    
def fetch_key():
    """
        Fetch the API from frappe conf and set in cache
    """
    cached_api = frappe.cache().get_value('zenquotes_api')
    
    if not cached_api:
        cached_api = frappe.local.conf.zenquotes_api_a or frappe.get_doc("ONEFM General Setting",None).get_password('zenquotes_api_key')
        if not cached_api:
            return response("Bad Request", 400, None, f"Zenquotes API Key not found")       
        frappe.cache().set_value('zenquotes_api',cached_api)
    return cached_api


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
        base_url = "https://quotes-api-gk4sqqu5rq-lm.a.run.app/quotes/list"
        keyword = fetch_keyword().lower()
        res = requests.post(base_url, {'category':keyword, 'count':1})
        if res.status_code in [200, 201]:
            data = res.json()
            if data.get('results'):
                return data
            else:
                return {}
        else:
            frappe.log_error(message=res.text, title="Error fetching Quote")
            return {}
    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Error fetching Quote")
        return {}