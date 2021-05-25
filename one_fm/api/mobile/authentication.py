import frappe
import pyotp
from frappe.twofactor import get_otpsecret_for_, process_2fa_for_sms, confirm_otp_token
from frappe.integrations.oauth2 import get_token
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.frappeclient import FrappeClient
from six import iteritems
from frappe import _
import requests, json
from one_fm.api.mobile.roster import get_current_user_details
from frappe.utils.password import update_password as _update_password


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
		response = session.post(
		 	"https://dev.one-fm.com/api/method/frappe.integrations.oauth2.get_token",
		 	data=args, headers=headers
		)

		if response.status_code == 200:
			conn = FrappeClient("https://dev.one-fm.com",username=username, password=password)
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
	

@frappe.whitelist(allow_guest=True)
def forgot_password(employee_id):
	"""
	Params: employee_id
	
	Returns: 
		Temp Id: To be used in next api call for verifying the SMS OTP. 
	Sends an OTP to mobile number assosciated with User	
	"""
	try:
		# employee_user_id = frappe.get_value("Employee", employee_id, "user_id")
		employee_user_id =  frappe.get_value("Employee", {'employee_id':employee_id}, 'user_id')
		otp_secret = get_otpsecret_for_(employee_user_id)
		token = int(pyotp.TOTP(otp_secret).now())
		tmp_id = frappe.generate_hash(length=8)
		cache_2fa_data(employee_user_id, token, otp_secret, tmp_id)
		verification_obj = process_2fa_for_sms(employee_user_id, token, otp_secret)

		# Save data in local
		# frappe.local.response['verification'] = verification_obj
		# frappe.local.response['tmp_id'] = tmp_id

		return {
			'message': _('Password reset instruction sms has been sent to your registered mobile number.'),
			'temp_id': tmp_id
		}

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
	pwd = frappe.form_dict.get('pwd')

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

