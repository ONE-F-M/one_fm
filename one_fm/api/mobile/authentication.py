import frappe
import pyotp
from frappe.twofactor import get_otpsecret_for_, process_2fa_for_sms, confirm_otp_token
from frappe.integrations.oauth2 import get_token
from six import iteritems
from frappe import _
import requests, json

@frappe.whitelist(allow_guest=True)
def login(client_id, grant_type, employee_id, password):
	username = frappe.get_value("Employee", employee_id, "user_id")
	if not username:
		return {'error': _('Employee ID is incorrect. Please check again.')}
	# login_manager = frappe.local.login_manager
	# login_manager.authenticate(employee_user_id, password)
	args = {
		'client_id': client_id,
		'grant_type': grant_type,
		'username': username,
		'password': password
	}
	print(args, dir(frappe.local.session_obj))

	session = requests.Session()

	# Login
	response = session.post(
		"http://192.168.0.152/api/method/frappe.integrations.oauth2.get_token",
		data=args
	)
	print(response.status_code, response.text)
	if response.status_code == 200:
		print(response.text)
		return response.json()
	else:
		return {'error': response.status_code}

	# return get_token(client_id, grant_type, username, password)
	# employee_phone_number = frappe.get_value("User", employee_user_id, "mobile_no")


@frappe.whitelist(allow_guest=True)
def signup(employee_id):
	employee_user_id = frappe.get_value("Employee", employee_id, "user_id")
	otp_secret = get_otpsecret_for_(employee_user_id)
	token = int(pyotp.TOTP(otp_secret).now())
	tmp_id = frappe.generate_hash(length=8)
	cache_2fa_data(employee_user_id, token, otp_secret, tmp_id)
	verification_obj = process_2fa_for_sms(employee_user_id, token, otp_secret)
	print(verification_obj, tmp_id, otp_secret)
	# Save data in local
	frappe.local.response['verification'] = verification_obj
	frappe.local.response['tmp_id'] = tmp_id
	return tmp_id

@frappe.whitelist(allow_guest=True)
def confirm_otp(otp, id):
	login_manager = frappe.local.login_manager
	confirm_otp_token(login_manager, otp, id) 
	return {
		'message': _('Verified successfully!')
	}

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


@frappe.whitelist(allow_guest=True)
def change_password():
	pass