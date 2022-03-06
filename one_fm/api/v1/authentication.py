import frappe
import pyotp
from frappe.twofactor import get_otpsecret_for_, process_2fa_for_sms, confirm_otp_token,get_email_subject_for_2fa,get_email_body_for_2fa
from frappe.integrations.oauth2 import get_token
from frappe.utils.background_jobs import enqueue
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.frappeclient import FrappeClient
from six import iteritems
from frappe import _
import requests, json
from frappe.utils.password import update_password as _update_password
from twilio.rest import Client as TwilioClient
from one_fm.api.v1.utils import response
from one_fm.processor import sendemail


@frappe.whitelist(allow_guest=True)
def login(client_id: str = None, grant_type: str = None, employee_id: str = None, password: str = None) -> dict:
	""" This method logs in the user provided appropriate paramaters.

	Args:
		client_id (str): Can be found in Social Login Key doctype.
		grant_type (str): password
		employee_id (str): Employee Id of user
		password (str): Erpnext Password

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (dict): { 
				access_token (str), 
				expires_in (int), 
				token_type (str) -> "Bearer", 
				scope (str), 
				refresh_token (str), 
				name (str), 
				employee_id (str), 
				employee_name (str), 
				image (str), 
				enrolled (int) -> 0/1, 
				designation (str), 
				roles (List[str]), 
				supervisor (int) -> 0/1
			}
			error (str)[Optional]: Any error response provided by server. 
		}
	"""
	if not client_id:
		return response("Bad Request", 400, None, "client_id is required!.")
	
	if not grant_type:
		return response("Bad Request", 400, None, "grant_type is required!")
	
	if not employee_id:
		return response("Bad Request", 400, None, "Employee ID is required!")
	
	if not password:
		return response("Bad Request", 400, None, "Password is required!")

	if not isinstance(client_id, str):
		return response("Bad Request", 400, None, "client_id must be of type str!")
	
	if not isinstance(grant_type, str):
		return response("Bad Request", 400, None, "grant_type must be of type str!")
	
	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "employee_id must be of type str!")

	if not isinstance(password, str):
		return response("Bad Request", 400, None, "password must be of type str!")
	
	try:
		site = frappe.utils.cstr(frappe.local.conf.app_url)
		username =  frappe.db.get_value("Employee", {'employee_id': employee_id}, 'user_id')
		
		if not username:
			return response("Unauthorized", 401, None, "Invalid employee ID")
		
		args = {
            'client_id': client_id,
            'grant_type': grant_type,
            'username': username,
            'password': password
        }
		headers = {'Accept': 'application/json'}
		session = requests.Session()

		auth_api = site + "api/method/frappe.integrations.oauth2.get_token"
		
		auth_api_response = session.post(
            auth_api,
            data=args, headers=headers
        )

		if auth_api_response.status_code == 200:
			
			frappe_client = FrappeClient(site[:-1], username=username, password=password)
			user, user_roles, user_employee =  frappe_client.get_api("one_fm.api.v1.utils.get_current_user_details")
			result = auth_api_response.json()
			result.update(user_employee)
			result.update({"roles": user_roles})
			if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles:
				result.update({"supervisor": 1})
			else:
				result.update({"supervisor": 0})

			return response("Success", 200, result)
		
		else:
			raw_error = json.loads(auth_api_response.content)
			if "message" in list(raw_error.keys()):
				return response("Bad Request", auth_api_response.status_code, None, raw_error['message'])
			
			return response("Bad Request", auth_api_response.status_code, None, json.loads(auth_api_response.content))

	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist(allow_guest=True)
def forgot_password(employee_id: str = None, otp_source: str = None) -> dict:
	"""Sends an OTP to mobile number assosciated with user.	

	Args:
		employee_id (str, optional): Employee ID of the user.
		otp_source (str, optional): OTP method to be used => sms/email/whatsapp.

	Returns:
		response (dict): {
			message (str): Brief message indicating the response.
			data (str): Password reset instructions sent via the otp source.
			error (str)[Optional]: Any error response provided by server. 
		}
	"""

	if not employee_id:
		return response("Bad Request", 400, None, "Employee ID required.")

	if not otp_source:
		return response("Bad Request", 400, None, "OTP source required.")

	if not isinstance(employee_id, str):
		return response("Bad Request", 400, None, "Employee ID must be of type str.")

	if not isinstance(otp_source, str):
		return response("Bad Request", 400, None, "OTP source must be of type str.")

	if otp_source.lower() not in ["sms", "email", "whatsapp"]:
		return response("Bad Request", 400, None, "Invalid OTP source. OTP source must be either 'sms', 'email' or 'whatsapp'.")
	
	try:
		employee_user_id =  frappe.get_value("Employee", {'employee_id': employee_id}, 'user_id')
		
		if not employee_user_id:
			return response("Bad Request", 404, None, "No user ID found for employee ID {employee_id}.".format(employee_id=employee_id))
		
		otp_secret = get_otpsecret_for_(employee_user_id)
		token = int(pyotp.TOTP(otp_secret).now())
		tmp_id = frappe.generate_hash(length=8)
		cache_2fa_data(employee_user_id, token, otp_secret, tmp_id)
		
		if otp_source.lower() == "sms":
			verification_obj = process_2fa_for_sms(employee_user_id, token, otp_secret)
			
		elif otp_source.lower() == "email":
			verification_obj = process_2fa_for_email(employee_user_id, token, otp_secret)
			
		elif otp_source.lower() == "whatsapp":
			verification_obj = process_2fa_for_whatsapp(employee_user_id, token, otp_secret)
		
		return response("Success", 201, "Password reset instructions sent via {otp_source}".format(otp_source=otp_source))
	
	except Exception as error:
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist(allow_guest=True)
def update_password(otp, id, employee_id, new_password):
	"""
	Params: 
	otp: OTP received via SMS
	id: Temp Id returned in forgot_password call response
	employee_id 
	new_password : new password to update
	"""
	try:
		login_manager = frappe.local.login_manager
		if confirm_otp_token(login_manager, otp, id):
			user_id = frappe.get_value("Employee", {'employee_id':employee_id}, ["user_id"])
			_update_password(user_id, new_password)
		return {
			'message': _('Password Updated!')
		}
	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

		
def cache_2fa_data(user, token, otp_secret, tmp_id):
	'''Cache and set expiry for data.'''
	# Temp password
	pwd = '12345'
	
	expiry_time = 1800
	
	frappe.cache().set(tmp_id + '_token', token)
	frappe.cache().expire(tmp_id + '_token', expiry_time)
	for k, v in iteritems({'_usr': user, '_pwd': pwd, '_otp_secret': otp_secret}):
		frappe.cache().set("{0}{1}".format(tmp_id, k), v)
		frappe.cache().expire("{0}{1}".format(tmp_id, k), expiry_time)

def process_2fa_for_whatsapp(user, token, otp_secret):
    '''Process sms method for 2fa.'''
    phone = frappe.db.get_value('User', user, ['phone', 'mobile_no'], as_dict=1)
    phone = phone.mobile_no or phone.phone
    status = send_token_via_whatsapp(otp_secret, token=token, phone_no=phone)
    verification_obj = {
        'token_delivery': status,
        'prompt': status and 'Enter verification code sent to {}'.format(phone[:4] + '******' + phone[-3:]),
        'method': 'SMS',
        'setup': status
    }
    return verification_obj


def send_token_via_whatsapp(otpsecret, token=None, phone_no=None):
    sid, auth_token, t_number = frappe.db.get_value('Twilio Setting', filters=None, fieldname=['sid','token','t_number'])
    client = TwilioClient(sid, auth_token)
    From = 'whatsapp:' + t_number
    to = 'whatsapp:+' + phone_no
    hotp = pyotp.HOTP(otpsecret)
    body= 'Your verification code {}.'.format(hotp.at(int(token)))
    
    message = client.messages.create( 
                              from_=From,  
                              body=body,      
                              to=to 
                          ) 
 
    return True

def process_2fa_for_email(user, token, otp_secret, method='Email'):
	otp_issuer = frappe.db.get_value('System Settings', 'System Settings', 'otp_issuer_name')
	'''Process Email method for 2fa.'''
	subject = None
	message = None
	status = True
	prompt = ''
	'''Sending email verification'''
	prompt = _('Verification code has been sent to your registered email address.')
	status = send_token_via_email(user, token, otp_secret, otp_issuer, subject=subject, message=message)
	verification_obj = {
		'token_delivery': status,
		'prompt': status and prompt,
		'method': 'Email',
		'setup': status
	}
	return verification_obj

def send_token_via_email(user, token, otp_secret, otp_issuer, subject=None, message=None):
	'''Send token to user as email.'''
	user_email = frappe.db.get_value('Employee', {"user_id":user}, 'personal_email')
	if not user_email:
		return False
	hotp = pyotp.HOTP(otp_secret)
	otp = hotp.at(int(token))
	template_args = {'otp': otp, 'otp_issuer': otp_issuer}
	if not subject:
		subject = get_email_subject_for_2fa(template_args)
	if not message:
		message = get_email_body_for_2fa(template_args)

	email_args = {
		'recipients': user_email,
		'sender': None,
		'subject': subject,
		'message': message,
		'header': [_('Verfication Code'), 'blue'],
		'delayed': False,
		'retry':3
	}

	enqueue(method=sendemail, queue='short', timeout=300, event=None,
		is_async=True, job_name=None, now=False, **email_args)
	return True
