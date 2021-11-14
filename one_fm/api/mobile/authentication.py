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
from one_fm.api.mobile.roster import get_current_user_details
from frappe.utils.password import update_password as _update_password
from twilio.rest import Client 

@frappe.whitelist(allow_guest=True)
def login(client_id, grant_type, employee_id, password):

	"""
	Params:
	Client Id: Can be found in Social Login Key doctype.
	Grant_type: implicit
	Employee Id: Employee Id of user
	Password: Erpnext Password 

	Returns: 
		Access token, refresh token, Enrollment status for checkin, Employee Id, Employee name, Employee image, Employee/Supervisor flag. 
	"""
	try:
		site = frappe.utils.cstr(frappe.local.site)
		# username = frappe.get_value("Employee", employee_id, "user_id")
		username =  frappe.get_value("Employee", {'employee_id':employee_id}, 'user_id')
		if not username:
			return {'error': _('Employee ID is incorrect. Please check again.')}
		args = {
			'client_id': client_id,
			'grant_type': grant_type,
			'username': username,
			'password': password
		}
		headers = {'Accept': 'application/json'}
		session = requests.Session()

		# Login
		auth_api = site + "/api/method/frappe.integrations.oauth2.get_token"
		response = session.post(
		 	auth_api,
		 	data=args, headers=headers
		)

		if response.status_code == 200:
			conn = FrappeClient(site,username=username, password=password)
			user, user_roles, user_employee =  conn.get_api("one_fm.api.mobile.roster.get_current_user_details")
			res = response.json()
			res.update(user_employee)
			res.update({"roles": user_roles})
			if "Operations Manager" in user_roles or "Projects Manager" in user_roles or "Site Supervisor" in user_roles:
				res.update({"supervisor": 1})
			else:
				res.update({"supervisor": 0})

			return res
		else:
			frappe.throw(_(response.text))

	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

def change_enroll_status(employee):
	 doc = frappe.get_doc("Employee", employee)
	 doc.enrolled = 0
	 doc.save(ignore_permissions=True)
	 frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def forgot_password(employee_id,OTP_source):
	"""
	Params: 
	employee_id: employee ID
	OTP_source: SMS, Email or WhatsApp
	
	Returns: 
		Temp Id: To be used in next api call for verifying the SMS/Email OTP. 
	Sends an OTP to mobile number assosciated with User	
	"""
	try:
		# employee_user_id = frappe.get_value("Employee", employee_id, "user_id")
		employee_user_id =  frappe.get_value("Employee", {'employee_id':employee_id}, 'user_id')
		otp_secret = get_otpsecret_for_(employee_user_id)
		token = int(pyotp.TOTP(otp_secret).now())
		tmp_id = frappe.generate_hash(length=8)
		cache_2fa_data(employee_user_id, token, otp_secret, tmp_id)
		if OTP_source=="SMS":
			verification_obj = process_2fa_for_sms(employee_user_id, token, otp_secret)
			return {
			'message': _('Password reset instruction sms has been sent to your registered mobile number.'),
			'temp_id': tmp_id
			}
		elif OTP_source=="Email":
			verification_obj = process_2fa_for_email(employee_user_id, token, otp_secret)
			return {
			'message': _('Password reset instruction email has been sent to your Email Address.'),
			'temp_id': tmp_id
			}
		elif OTP_source=="WhatsApp":
			verification_obj = process_2fa_for_whatsapp(employee_user_id, token, otp_secret)
			return {
			'message': _('Password reset instruction message has been sent to your WhatsApp.'),
			'temp_id': tmp_id
			}
		else:
			return ('Please Select where you want your OTP to be sent.')

		# Save data in local
		# frappe.local.response['verification'] = verification_obj
		# frappe.local.response['tmp_id'] = tmp_id

	except Exception as e:
		return frappe.utils.response.report_error(e.http_status_code)

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
	# pwd = frappe.form_dict.get('pwd')

	#hardcode the pwd for time being.
	pwd = '12345'
	# set increased expiry time for SMS and Email
	expiry_time = 1800
	frappe.cache().set(tmp_id + '_token', token)
	frappe.cache().expire(tmp_id + '_token', expiry_time)
	for k, v in iteritems({'_usr': user, '_pwd': pwd, '_otp_secret': otp_secret}):
		frappe.cache().set("{0}{1}".format(tmp_id, k), v)
		frappe.cache().expire("{0}{1}".format(tmp_id, k), expiry_time)


#Not needed or being used
def signup(employee_id):
	try:
		user = frappe.get_value("Employee", {'employee_id':employee_id}, 'user_id')
		if user=="Administrator":
			return 'not allowed'

		user = frappe.get_doc("User", user)
		if not user.enabled:
			return 'disabled'

		user.validate_reset_password()
		reset_password(user)

		return {
		'message': _('Password reset instruction sms has been sent to your registered mobile number.')
		}

	except frappe.DoesNotExistError:
		frappe.clear_messages()
		return frappe.utils.response.report_error(e.http_status_code)

# Not needed or being used
def reset_password(user, password_expired=False):
	from frappe.utils import random_string, get_url

	key = random_string(32)
	user.db_set("reset_password_key", key)

	url = "/update-password?key=" + key
	if password_expired:
		url = "/update-password?key=" + key + '&password_expired=true'

	link = get_url(url)
	
	msg = """Dear {username},

		Please click on the following link to reset your password:
		{link}
	""".format(username=user.full_name, link=link)

	send_sms([user.mobile_no], msg)


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
    Twilio= frappe.db.get_value('Twilio Setting', filters=None, fieldname=['sid','token','t_number'])
    account_sid = Twilio[0]
    auth_token = Twilio[2]
    client = Client(account_sid, auth_token)
    From = 'whatsapp:' + Twilio[1]
    to = 'whatsapp:+' + phone_no
    hotp = pyotp.HOTP(otpsecret)
    body= 'Your verification code {}.'.format(hotp.at(int(token)))
    
    message = client.messages.create( 
                              from_=From,  
                              body=body,      
                              to=to 
                          ) 
 
    print(message.sid)
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

	enqueue(method=frappe.sendmail, queue='short', timeout=300, event=None,
		is_async=True, job_name=None, now=False, **email_args)
	return True
