# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CountryCallingCode(Document):
	pass

def create_country_code():
	list_of_country_code = [
		{ "country": "Afghanistan", "country_code": "+93", "code": "AF" },
		{ "country": "Åland Islands", "country_code": "+358", "code": "AX" }, { "country": "Albania", "country_code": "+355", "code": "AL" },
		{ "country": "Algeria", "country_code": "+213", "code": "DZ" }, { "country": "American Samoa", "country_code": "+1684", "code": "AS" },
		{ "country": "Andorra", "country_code": "+376", "code": "AD" }, { "country": "Angola", "country_code": "+244", "code": "AO" },
		{ "country": "Anguilla", "country_code": "+1264", "code": "AI" }, { "country": "Antarctica", "country_code": "+672", "code": "AQ" },
		{ "country": "Antigua and Barbuda", "country_code": "+1268", "code": "AG" }, { "country": "Argentina", "country_code": "+54", "code": "AR" },
		{ "country": "Armenia", "country_code": "+374", "code": "AM" }, { "country": "Aruba", "country_code": "+297", "code": "AW" },
		{ "country": "Australia", "country_code": "+61", "code": "AU" }, { "country": "Austria", "country_code": "+43", "code": "AT" },
		{ "country": "Azerbaijan", "country_code": "+994", "code": "AZ" }, { "country": "Bahamas", "country_code": "+1242", "code": "BS" },
		{ "country": "Bahrain", "country_code": "+973", "code": "BH" }, { "country": "Bangladesh", "country_code": "+880", "code": "BD" },
		{ "country": "Barbados", "country_code": "+1246", "code": "BB" }, { "country": "Belarus", "country_code": "+375", "code": "BY" },
		{ "country": "Belgium", "country_code": "+32", "code": "BE" }, { "country": "Belize", "country_code": "+501", "code": "BZ" },
		{ "country": "Benin", "country_code": "+229", "code": "BJ" }, { "country": "Bermuda", "country_code": "+1441", "code": "BM" },
		{ "country": "Bhutan", "country_code": "+975", "code": "BT" },
		{ "country": "Bolivia, Plurinational State of bolivia", "country_code": "+591", "code": "BO" },
		{ "country": "Bosnia and Herzegovina", "country_code": "+387", "code": "BA" },
		{ "country": "Botswana", "country_code": "+267", "code": "BW" }, { "country": "Bouvet Island", "country_code": "+47", "code": "BV" },
		{ "country": "Brazil", "country_code": "+55", "code": "BR" },
		{ "country": "British Indian Ocean Territory", "country_code": "+246", "code": "IO" },
		{ "country":"Brunei Darussalam", "country_code": "+673", "code": "BN" }, { "country": "Bulgaria", "country_code": "+359", "code": "BG" },
		{ "country": "Burkina Faso", "country_code": "+226", "code": "BF" }, { "country": "Burundi", "country_code": "+257", "code": "BI" },
		{ "country": "Cambodia", "country_code": "+855", "code": "KH" }, { "country": "Cameroon", "country_code": "+237", "code": "CM" },
		{ "country": "Canada", "country_code": "+1", "code": "CA" }, { "country": "Cape Verde", "country_code": "+238", "code": "CV" },
		{ "country": "Cayman Islands", "country_code": "+ 345", "code": "KY" },
		{ "country": "Central African Republic", "country_code": "+236", "code": "CF" },
		{ "country": "Chad", "country_code": "+235", "code": "TD" }, { "country": "Chile", "country_code": "+56", "code": "CL" },
		{ "country": "China", "country_code": "+86", "code": "CN" }, { "country": "Christmas Island", "country_code": "+61", "code": "CX" },
		{ "country": "Cocos (Keeling) Islands", "country_code": "+61", "code": "CC" },
		{ "country": "Colombia", "country_code": "+57", "code": "CO" }, { "country": "Comoros", "country_code": "+269", "code": "KM" },
		{ "country": "Congo", "country_code": "+242", "code": "CG" },
		{ "country": "Congo, The Democratic Republic of the Congo", "country_code": "+243", "code": "CD" },
		{ "country": "Cook Islands", "country_code": "+682", "code": "CK" }, { "country": "Costa Rica", "country_code": "+506", "code": "CR" },
		{ "country": "Cote d'Ivoire", "country_code": "+225", "code": "CI" }, { "country": "Croatia", "country_code": "+385", "code": "HR" },
		{ "country": "Cuba", "country_code": "+53", "code": "CU" }, { "country": "Cyprus", "country_code": "+357", "code": "CY" },
		{ "country": "Czech Republic", "country_code": "+420", "code": "CZ" },
		{ "country": "Denmark", "country_code": "+45", "code": "DK" }, { "country": "Djibouti", "country_code": "+253", "code": "DJ" },
		{ "country": "Dominica", "country_code": "+1767", "code": "DM" }, { "country": "Dominican Republic", "country_code": "+1849", "code": "DO" },
		{ "country": "Ecuador", "country_code": "+593", "code": "EC" }, { "country": "Egypt", "country_code": "+20", "code": "EG" },
		{ "country": "El Salvador", "country_code": "+503", "code": "SV" }, { "country": "Equatorial Guinea", "country_code": "+240", "code": "GQ" },
		{ "country": "Eritrea", "country_code": "+291", "code": "ER" }, { "country": "Estonia", "country_code": "+372", "code": "EE" },
		{ "country": "Ethiopia", "country_code": "+251", "code": "ET" },
		{ "country": "Falkland Islands (Malvinas)", "country_code": "+500", "code": "FK" },
		{ "country": "Faroe Islands", "country_code": "+298", "code": "FO" }, { "country": "Fiji", "country_code": "+679", "code": "FJ" },
		{ "country": "Finland", "country_code": "+358", "code": "FI" }, { "country": "France", "country_code": "+33", "code": "FR" },
		{ "country": "French Guiana", "country_code": "+594", "code": "GF" },
		{ "country": "French Polynesia", "country_code": "+689", "code": "PF" },
		{ "country": "French Southern Territories", "country_code": "+262", "code": "TF" },
		{ "country": "Gabon", "country_code": "+241", "code": "GA" }, { "country": "Gambia", "country_code": "+220", "code": "GM" },
		{ "country": "Georgia", "country_code": "+995", "code": "GE" }, { "country": "Germany", "country_code": "+49", "code": "DE" },
		{ "country": "Ghana", "country_code": "+233", "code": "GH" },
		{ "country": "Gibraltar", "country_code": "+350", "code": "GI" }, { "country": "Greece", "country_code": "+30", "code": "GR" },
		{ "country": "Greenland", "country_code": "+299", "code": "GL" }, { "country": "Grenada", "country_code": "+1473", "code": "GD" },
		{ "country": "Guadeloupe", "country_code": "+590", "code": "GP" }, { "country": "Guam", "country_code": "+1671", "code": "GU" },
		{ "country": "Guatemala", "country_code": "+502", "code": "GT" }, { "country": "Guernsey", "country_code": "+44", "code": "GG" },
		{ "country": "Guinea", "country_code": "+224", "code": "GN" }, { "country": "Guinea-Bissau", "country_code": "+245", "code": "GW" },
		{ "country": "Guyana", "country_code": "+592", "code": "GY" }, { "country": "Haiti", "country_code": "+509", "code": "HT" },
		{ "country": "Heard Island and Mcdonald Islands", "country_code": "+0", "code": "HM" },
		{ "country": "Holy See (Vatican City State)", "country_code": "+379", "code": "VA" },
		{ "country": "Honduras", "country_code": "+504", "code": "HN" }, { "country": "Hong Kong", "country_code": "+852", "code": "HK" },
		{ "country": "Hungary", "country_code": "+36", "code": "HU" }, { "country": "Iceland", "country_code": "+354", "code": "IS" },
		{ "country": "India", "country_code": "+91", "code": "IN" }, { "country": "Indonesia", "country_code": "+62", "code": "ID" },
		{ "country": "Iran, Islamic Republic of Persian Gulf", "country_code": "+98", "code": "IR" },
		{ "country": "Iraq", "country_code": "+964", "code": "IQ" }, { "country": "Ireland", "country_code": "+353", "code": "IE" },
		{ "country": "Isle of Man", "country_code": "+44", "code": "IM" },
		{ "country": "Israel", "country_code": "+972", "code": "IL" }, { "country": "Italy", "country_code": "+39", "code": "IT" },
		{ "country": "Jamaica", "country_code": "+1876", "code": "JM" }, { "country": "Japan", "country_code": "+81", "code": "JP" },
		{ "country": "Jersey", "country_code": "+44", "code": "JE" }, { "country": "Jordan", "country_code": "+962", "code": "JO" },
		{ "country": "Kazakhstan", "country_code": "+7", "code": "KZ" }, { "country": "Kenya", "country_code": "+254", "code": "KE" },
		{ "country": "Kiribati", "country_code": "+686", "code": "KI" },
		{ "country": "Korea, Democratic People's Republic of Korea", "country_code": "+850", "code": "KP" },
		{ "country": "Korea, Republic of South Korea", "country_code": "+82", "code": "KR" },
		{ "country": "Kosovo", "country_code": "+383", "code": "XK" }, { "country": "Kuwait", "country_code": "+965", "code": "KW" },
		{ "country": "Kyrgyzstan", "country_code": "+996", "code": "KG" }, { "country": "Laos", "country_code": "+856", "code": "LA" },
		{ "country": "Latvia", "country_code": "+371", "code": "LV" },
		{ "country": "Lebanon", "country_code": "+961", "code": "LB" }, { "country": "Lesotho", "country_code": "+266", "code": "LS" },
		{ "country": "Liberia", "country_code": "+231", "code": "LR" },
		{ "country": "Libyan Arab Jamahiriya", "country_code": "+218", "code": "LY" },
		{ "country": "Liechtenstein", "country_code": "+423", "code": "LI" }, { "country": "Lithuania", "country_code": "+370", "code": "LT" },
		{ "country": "Luxembourg", "country_code": "+352", "code": "LU" }, { "country": "Macao", "country_code": "+853", "code": "MO" },
		{ "country": "Macedonia", "country_code": "+389", "code": "MK" }, { "country": "Madagascar", "country_code": "+261", "code": "MG" },
		{ "country": "Malawi", "country_code": "+265", "code": "MW" }, { "country": "Malaysia", "country_code": "+60", "code": "MY" },
		{ "country": "Maldives", "country_code": "+960", "code": "MV" }, { "country": "Mali", "country_code": "+223", "code": "ML" },
		{ "country": "Malta", "country_code": "+356", "code": "MT" }, { "country": "Marshall Islands", "country_code": "+692", "code": "MH" },
		{ "country": "Martinique", "country_code": "+596", "code": "MQ" }, { "country": "Mauritania", "country_code": "+222", "code": "MR" },
		{ "country": "Mauritius", "country_code": "+230", "code": "MU" }, { "country": "Mayotte", "country_code": "+262", "code": "YT" },
		{ "country": "Mexico", "country_code": "+52", "code": "MX" },
		{ "country": "Micronesia, Federated States of Micronesia", "country_code": "+691", "code": "FM" },
		{ "country": "Moldova", "country_code": "+373", "code": "MD" }, { "country": "Monaco", "country_code": "+377", "code": "MC" },
		{ "country": "Mongolia", "country_code": "+976", "code": "MN" }, { "country": "Montenegro", "country_code": "+382", "code": "ME" },
		{ "country": "Montserrat", "country_code": "+1664", "code": "MS" }, { "country": "Morocco", "country_code": "+212", "code": "MA" },
		{ "country": "Mozambique", "country_code": "+258", "code": "MZ" }, { "country": "Myanmar", "country_code": "+95", "code": "MM" },
		{ "country": "Namibia", "country_code": "+264", "code": "NA" }, { "country": "Nauru", "country_code": "+674", "code": "NR" },
		{ "country": "Nepal", "country_code": "+977", "code": "NP" }, { "country": "Netherlands", "country_code": "+31", "code": "NL" },
		{ "country": "Netherlands Antilles", "country_code": "+599", "code": "AN" },
		{ "country": "New Caledonia", "country_code": "+687", "code": "NC" }, { "country": "New Zealand", "country_code": "+64", "code": "NZ" },
		{ "country": "Nicaragua", "country_code": "+505", "code": "NI" }, { "country": "Niger", "country_code": "+227", "code": "NE" },
		{ "country": "Nigeria", "country_code": "+234", "code": "NG" },
		{ "country": "Niue", "country_code": "+683", "code": "NU" }, { "country": "Norfolk Island", "country_code": "+672", "code": "NF" },
		{ "country": "Northern Mariana Islands", "country_code": "+1670", "code": "MP" },
		{ "country": "Norway", "country_code": "+47", "code": "NO" }, { "country": "Oman", "country_code": "+968", "code": "OM" },
		{ "country": "Pakistan", "country_code": "+92", "code": "PK" }, { "country": "Palau", "country_code": "+680", "code": "PW" },
		{ "country": "Palestinian Territory, Occupied", "country_code": "+970", "code": "PS" },
		{ "country": "Panama", "country_code": "+507", "code": "PA" }, { "country": "Papua New Guinea", "country_code": "+675", "code": "PG" },
		{ "country": "Paraguay", "country_code": "+595", "code": "PY" }, { "country": "Peru", "country_code": "+51", "code": "PE" },
		{ "country": "Philippines", "country_code": "+63", "code": "PH" }, { "country": "Pitcairn", "country_code": "+64", "code": "PN" },
		{ "country": "Poland", "country_code": "+48", "code": "PL" }, { "country": "Portugal", "country_code": "+351", "code": "PT" },
		{ "country": "Puerto Rico", "country_code": "+1939", "code": "PR" }, { "country": "Qatar", "country_code": "+974", "code": "QA" },
		{ "country": "Romania", "country_code": "+40", "code": "RO" }, { "country": "Russia", "country_code": "+7", "code": "RU" },
		{ "country": "Rwanda", "country_code": "+250", "code": "RW" }, { "country": "Reunion", "country_code": "+262", "code": "RE" },
		{ "country": "Saint Barthelemy", "country_code": "+590", "code": "BL" },
		{ "country": "Saint Helena, Ascension and Tristan Da Cunha", "country_code": "+290", "code": "SH" },
		{ "country": "Saint Kitts and Nevis", "country_code": "+1869", "code": "KN" },
		{ "country": "Saint Lucia", "country_code": "+1758", "code": "LC" }, { "country": "Saint Martin", "country_code": "+590", "code": "MF" },
		{ "country": "Saint Pierre and Miquelon", "country_code": "+508", "code": "PM" },
		{ "country": "Saint Vincent and the Grenadines", "country_code": "+1784", "code": "VC" },
		{ "country": "Samoa", "country_code": "+685", "code": "WS" }, { "country": "San Marino", "country_code": "+378", "code": "SM" },
		{ "country": "Sao Tome and Principe", "country_code": "+239", "code": "ST" },
		{ "country": "Saudi Arabia", "country_code": "+966", "code": "SA" }, { "country": "Senegal", "country_code": "+221", "code": "SN" },
		{ "country": "Serbia", "country_code": "+381", "code": "RS" }, { "country": "Seychelles", "country_code": "+248", "code": "SC" },
		{ "country": "Sierra Leone", "country_code": "+232", "code": "SL" }, { "country": "Singapore", "country_code": "+65", "code": "SG" },
		{ "country": "Slovakia", "country_code": "+421", "code": "SK" },
		{ "country": "Slovenia", "country_code": "+386", "code": "SI" }, { "country": "Solomon Islands", "country_code": "+677", "code": "SB" },
		{ "country": "Somalia", "country_code": "+252", "code": "SO" }, { "country": "South Africa", "country_code": "+27", "code": "ZA" },
		{ "country": "South Sudan", "country_code": "+211", "code": "SS" },
		{ "country": "South Georgia and the South Sandwich Islands", "country_code": "+500", "code": "GS" },
		{ "country": "Spain", "country_code": "+34", "code": "ES" }, { "country": "Sri Lanka", "country_code": "+94", "code": "LK" },
		{ "country": "Sudan", "country_code": "+249", "code": "SD" }, { "country": "Suriname", "country_code": "+597", "code": "SR" },
		{ "country": "Svalbard and Jan Mayen", "country_code": "+47", "code": "SJ" },
		{ "country": "Swaziland", "country_code": "+268", "code": "SZ" }, { "country": "Sweden", "country_code": "+46", "code": "SE" },
		{ "country": "Switzerland", "country_code": "+41", "code": "CH" },
		{ "country": "Syrian Arab Republic", "country_code": "+963", "code": "SY" },
		{ "country": "Taiwan", "country_code": "+886", "code": "TW" },
		{ "country": "Tajikistan", "country_code": "+992", "code": "TJ" },
		{ "country": "Tanzania, United Republic of Tanzania", "country_code": "+255", "code": "TZ" },
		{ "country": "Thailand", "country_code": "+66", "code": "TH" }, { "country": "Timor-Leste", "country_code": "+670", "code": "TL" },
		{ "country": "Togo", "country_code": "+228", "code": "TG" }, { "country": "Tokelau", "country_code": "+690", "code": "TK" },
		{ "country": "Tonga", "country_code": "+676", "code": "TO" }, { "country": "Trinidad and Tobago", "country_code": "+1868", "code": "TT" },
		{ "country": "Tunisia", "country_code": "+216", "code": "TN" }, { "country": "Turkey", "country_code": "+90", "code": "TR" },
		{ "country": "Turkmenistan", "country_code": "+993", "code": "TM" },
		{ "country": "Turks and Caicos Islands", "country_code": "+1649", "code": "TC" },
		{ "country": "Tuvalu", "country_code": "+688", "code": "TV" }, { "country": "Uganda", "country_code": "+256", "code": "UG" },
		{ "country": "Ukraine", "country_code": "+380", "code": "UA" }, { "country": "United Arab Emirates", "country_code": "+971", "code": "AE" },
		{ "country": "United Kingdom", "country_code": "+44", "code": "GB" }, { "country": "United States", "country_code": "+1", "code": "US" },
		{ "country": "Uruguay", "country_code": "+598", "code": "UY" }, { "country": "Uzbekistan", "country_code": "+998", "code": "UZ" },
		{ "country": "Vanuatu", "country_code": "+678", "code": "VU" },
		{ "country": "Venezuela, Bolivarian Republic of Venezuela", "country_code": "+58", "code": "VE" },
		{ "country": "Vietnam", "country_code": "+84", "code": "VN" },
		{ "country": "Virgin Islands, British", "country_code": "+1284", "code": "VG" },
		{ "country": "Virgin Islands, U.S.", "country_code": "+1340", "code": "VI" },
		{ "country": "Wallis and Futuna", "country_code": "+681", "code": "WF" }, { "country": "Yemen", "country_code": "+967", "code": "YE" },
		{ "country": "Zambia", "country_code": "+260", "code": "ZM" }, { "country": "Zimbabwe", "country_code": "+263", "code": "ZW" }
	]

	for country in list_of_country_code:
		if frappe.db.exists('Country', country['country']):
			if not frappe.db.exists('Country Calling Code', country['country_code']):
				country_calling_code = frappe.new_doc('Country Calling Code')
				country_calling_code.country_code = country['country_code']
				country_calling_code.country = country['country']
				country_calling_code.save(ignore_permissions=True)
				frappe.db.commit()
				print(country_calling_code.country)
				print(country_calling_code.name)
