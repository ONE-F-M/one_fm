import frappe
import pyotp
from frappe.utils import getdate
from frappe.twofactor import get_otpsecret_for_, process_2fa_for_sms, confirm_otp_token, get_email_subject_for_2fa,get_email_body_for_2fa
from frappe.integrations.oauth2 import get_token
from frappe.core.doctype.user.user import generate_keys
from frappe.utils.background_jobs import enqueue
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.frappeclient import FrappeClient
from frappe.utils import now_datetime
from six import iteritems
from frappe import _
import requests, json
from frappe.utils.password import update_password as _update_password
from twilio.rest import Client as TwilioClient
from one_fm.api.v1.utils import response, get_current_user_details
from one_fm.processor import sendemail, send_whatsapp

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
				registered (int) -> 0/1,  
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
		frappe.log_error(title="API Login", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)

@frappe.whitelist(allow_guest=True)
def forgot_password(employee_id: str = None, otp_source: str = None, is_new: int = 0) -> dict:
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
		
		password_token = frappe.get_doc({
			"doctype":"Password Reset Token",
			"user":employee_user_id,
			"status": 'Inactive',
			"temp_id":tmp_id,
			"new_password": 1 if is_new else 0
		}).insert(ignore_permissions=True)

		result = {
			"message": "Password reset instructions sent via {otp_source}".format(otp_source=otp_source),
			"temp_id": tmp_id
		}

		return response("Success", 201, result)
	
	except Exception as error:
		frappe.log_error(title="API Forgot password", message=frappe.get_traceback())
		return response("Internal Server Error", 500, None, error)


@frappe.whitelist(allow_guest=True)
def verify_otp(otp, temp_id):
	"""
	verifies the OTP entered by the employee

	params
	otp
	temp_id


	returns
	status of the OTP entered 
	"""
	try:
		login_manager = frappe.local.login_manager
		check_otp = confirm_otp_token(login_manager, otp, temp_id)
		#  get password reset
		password_token = frappe.db.get_value(
			"Password Reset Token",
			{"temp_id":temp_id}, 
			['name', 'status', 'expiration_time'],
			as_dict=1
		)
		if check_otp:
			frappe.db.set_value("Password Reset Token", {"temp_id":temp_id}, "status", "Active")
			return response ("success", 200, {
				"password_token":password_token.name,
				"message":"OTP verified Successfully !"})
		frappe.db.set_value("Password Reset Token", {"temp_id":temp_id}, "status", "Revoked")
		return response("Error", 400, {}, "invalid OTP")
	except Exception as e:
		response("Error", 500, {}, str(e) or "OTP Verification Failed!")


@frappe.whitelist(allow_guest=True)
def change_password(employee_id, new_password, password_token):
	"""
	Params: 
	Employee ID: The ID of the employee
	new_password: new password to update
	password_token: will be used to verify the password reset and user
	"""
	try:
		employee_user = frappe.get_value("Employee", {'employee_id':employee_id}, ["user_id"])
		password_token_info = frappe.db.get_value(
			"Password Reset Token",
			{"name":password_token}, 
			['name', 'status', 'expiration_time', 'user', 'new_password'],
			as_dict=1
		)
		if (employee_user!=password_token_info.user):
			return response ("Error", 400, {}, "Invalid password reset user does not match.")
		elif password_token_info.status != "Active":
			return response ("Error", 400, {}, "Password token has expired.")

		_update_password(employee_user, new_password)
		frappe.db.set_value("Password Reset Token", password_token, "status", "Revoked")
		if password_token_info.new_password:
			frappe.db.set_value("Employee", {"employee_id":employee_id}, "registered", 1)
		return response ("Success", 200, {
			"message": "Password Reset Successful, please login to continue."
		}, "")
	except Exception as e:
		frappe.log_error(title="API Change password", message=frappe.get_traceback())
		return response ("Error", 500, {}, str(e))


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
		frappe.log_error(title="API Update password", message=frappe.get_traceback())
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
  
    hotp = pyotp.HOTP(otpsecret)
    content_variables= {
	                    	'1': hotp.at(int(token))
                    	}
    message = send_whatsapp(sender_id=phone_no,template_name='authentication_code', content_variables=content_variables)

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


@frappe.whitelist(allow_guest=True)
def validate_employee_id(employee_id=None):
	"""
	params
	employee_id -  the id of the employee, e.g 2107042EG187

	returns
	name_in_arabic
	name_in_english
	the registration status of the employee
	client_id
	"""
	if employee_id is None:
		return response("Employee ID cannot be None", 401, None, "Employee ID is required !")
	doc = frappe.get_doc("Employee",{ "employee_id": employee_id})
	if not doc:
		return response("Employee Not Found", 404, None, "Employee ID of an active Employee is required")
	registration_status = frappe.db.get_value("User", doc.user_id, "last_password_reset_date")
	client_id = frappe.db.get_value("OAuth Client", {"app_name": "OneFM" }, "client_id")
	data = {
		"name in arabic": doc.employee_name_in_arabic,
		"name in english": doc.employee_name,
		"is_registered": True if registration_status else False,
		"client_id": client_id,
		"is_enrolled": True if doc.enrolled else False,
		"is_registered": True if doc.registered else False
	}
	return response("Success", 200, data)

@frappe.whitelist()
def fetch_employee_checkin_list(from_date=None, to_date=None, limit=20, page_number=1):
	""""
	returns an array of check in objects which belongs to the logged in employee

	Params
	from_date - begining date
	to_date - ending date
	limit - paginated by how many objects
	page_number - page to jump to


	returns
	no_of_pages - Total number of pages based on the limit
	current_page
	data - array of paginated check in objects
	number_of_check_in - total number of check in objects
	
	"""
	try:
		user_id = frappe.session.user
		if user_id is None:
			return response("Invalid authentication Credentials", 400, None, "Valid Authentication credentials is Required !")
		employee = frappe.get_doc("Employee", {"user_id": user_id})
		if employee is None:
			return response("The user_Id doesnt belong to an employee", 400)
		if not isinstance(page_number, int):
			return response("Invalid page number", 400, None, "Page Number must be an Integer !")
		if not isinstance(limit, int):
			return response("Invalid Data Type ! ", 400, None, "Enter an integer! ")
		if from_date is not None and to_date is None:
			to_date = from_date 
		if from_date is not None:
			try:
				from_date = getdate(from_date)
			except:
				from_date = None
		if to_date is not None:
			try:
				to_date = getdate(to_date)
			except:
				to_date = None
		if from_date and to_date:
			if from_date > to_date:
				return response("Bad request", 400, None, "From_date cannot be greater than to date")
		check_list = frappe.db.get_list("Employee Checkin", filters={"employee": employee.name, "time": ["between", (from_date, to_date)]}, fields=["name", "time", "log_type"])
		if len(check_list) < 1:
			return response("No check in for this employee in this time range !", 200)
		no_of_pages = len(check_list) // limit if len(check_list) % limit == 0 and len(check_list) // limit > 0 else (len(check_list) // limit) + 1
		if page_number > no_of_pages or page_number < 1:
			return response("Page not found !", 404, None, f"Enter a page number within 1 - {no_of_pages}")
		end = page_number * limit
		check_in = check_list[(end - limit): end]
		data = {
			"no_of_pages": no_of_pages,
			"current_page": page_number,
			"data": check_in,
			"number of checkin": len(check_list)
		}
		return response("Successfully Retrieved !", 200, data)
	except Exception as e:
		frappe.log_error(title="API Authentication", message=frappe.get_traceback())
		response("Internal Server Error", 500, None, str(e))

@frappe.whitelist(allow_guest=True)
def new_forgot_password(employee_id=None):
	"""
	validates the employee_id and returns the employee_user_id, which will be used to generate OTP

	Params
	employee_id

	returns
	employee_user_id
	
	"""
	if not employee_id:
		return response("Bad Request", 400, None, "Employee ID required.")

	employee_user_id =  frappe.get_value("Employee", {'employee_id': employee_id}, 'user_id')
	
	if not employee_user_id:
		return response("Bad Request", 404, None, "No user ID found for employee ID {employee_id}.".format(employee_id=employee_id))

	return response("success", 200, {"employee_user_id": employee_user_id})

@frappe.whitelist(allow_guest=True)
def get_otp(employee_user_id: str=None, otp_source: str=None):
	"""
	sends OTP to the employee 

	params
	emaployee_user_id
	otp_source - where you want the OTP to be sent to sms, whatsapp, mail


	returns
	success message
	temp_id - which would be used to verify the authenticity of the OTP
	
	"""
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

	result = {
		"message": "Password reset instructions sent via {otp_source}".format(otp_source=otp_source),
		"temp_id": tmp_id,
	}

	return response("Success", 201, result)


@frappe.whitelist(allow_guest=True)
def set_password(employee_user_id, new_password):
	"""
	used to set the new password

	params
	new_password
	employee_user_id

	returns
	success message
	
	"""
	try:
		_update_password(employee_user_id, new_password)
		frappe.db.set_value("Employee", {'employee_id':employee_user_id}, "registered", 1)
		message =  {
				'message': _('Password Updated!')
			}
		return response("Success", 200, message)
	except Exception as e:
		return response("Error", 500, {}, str(e))

@frappe.whitelist(allow_guest=True)
def user_login(employee_id, password):
	try:
		username =  frappe.db.get_value("Employee", {'employee_id': employee_id}, 'user_id')
		if not username:
			return response("Unauthorized", 401, None, "Invalid employee ID")
		auth = frappe.auth.LoginManager()
		auth.authenticate(user=username, pwd=password)
		auth.post_login()
		msg={'status':200, 'text':frappe.local.response.message, 'user': frappe.session.user}
		user = frappe.get_doc('User', frappe.session.user)
		if(user.api_key and user.api_secret):
			msg['token'] = f"token {user.api_key}:{user.get_password('api_secret')}"
		else:
			session_user = frappe.session.user
			frappe.set_user('Administrator')
			generate_keys(user.name)
			user.reload()
			msg['token'] = f"token {user.api_key}:{user.get_password('api_secret')}"
			frappe.set_user(session_user)
		user, user_roles, user_employee =  get_current_user_details()
		msg.update(user_employee)
		msg.update({"roles": user_roles})
		if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles:
			msg.update({"supervisor": 1})
		else:
			msg.update({"supervisor": 0})
		response("success", 200, msg)
	except frappe.exceptions.AuthenticationError:
		print('auth eror')
		response("error", 401, None, frappe.local.response.message)
	except Exception as e:
		print(frappe.get_traceback(), 'Email Login')
		response("error", 500, None, str(e))


@frappe.whitelist(allow_guest=True)
def enrollment_status(employee_id: str):
	"""
	Check if employee is enrolled 

	params
	employee_id

	returns
	success message
	enrroled - True/False
	
	"""
	try:
		if not employee_id:
			return response("error", 404, "Employee ID is required")
		employee = frappe.db.get_value(
			'Employee', 
			{'employee_id':employee_id} 
			,['status', 'enrolled', 'registered', 'employee_name', 'user_id'], as_dict=1)
		if employee:
			if (employee.status in ['Left', 'Court Case']):
				return response("error", 404, {}, f"Employee is not active")
			elif (not employee.user_id):
				return response("error", 404, {}, f"Employee no active user account or login email.")
			else:
				return response("success", 200, {
					"enrolled": employee.enrolled,
					"registered": employee.registered, 
					"employee_name":employee.employee_name},
				)
		else:
			return response("error", 404, {}, f"Employee ID {employee_id} not not found")
	except Exception as e:
		return response("error", 500, {}, str(e))