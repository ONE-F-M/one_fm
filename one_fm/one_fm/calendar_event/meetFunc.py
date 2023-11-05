import os.path
import frappe
from frappe import _
import datefinder
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
from datetime import datetime, timedelta



class CalendarEvent:
    # Creates required directories to store authorization credentials for different users.
    def __init__(self, sessionUser):
        path1 = '/home/frappe/frappe-bench/apps/one_fm/one_fm/one_fm/calendar_event/'
        try:
            if not os.path.exists("{}{}/token.pkl".format(path1, sessionUser)):
                os.makedirs("{}{}".format(path1, sessionUser))
                print("Directory ", sessionUser,  " Created ")
            else:
                print("Directory ", sessionUser,  " already exists")
        except:
            frappe.throw(
                _('Something went wrong while generating token directories'))
        try:
            global service
            if os.path.isfile("{}{}/token.pkl".format(path1, sessionUser)):
                credentials = pickle.load(
                    open("{}{}/token.pkl".format(path1, sessionUser), "rb"))
                service = build('calendar', 'v3', credentials=credentials)
                result = service.calendarList().list().execute()
            else:
                frappe.throw(_('Could not find authorization token'))
                # SCOPES = ['https://www.googleapis.com/auth/calendar']
                # flow = InstalledAppFlow.from_client_secrets_file(
                #     '/home/frappe/frappe-bench/apps/one_fm/one_fm/one_fm/calendar_event/client_secret_692373747079-gfanujf6rcnrl2smdb30007mnvkmarbc.apps.googleusercontent.com.json', SCOPES)
                # credentials = flow.run_local_server()
                # print(credentials)
                # pickle.dump(credentials, open(
                #     "{}{}/token.pkl".format(path1, sessionUser), "wb"))
                # credentials = pickle.load(
                #     open("{}{}/token.pkl".format(path1, sessionUser), "rb"))
                # service = build('calendar', 'v3', credentials=credentials)
                # result = service.calendarList().list().execute()
        except:
            frappe.throw(_('Something went wrong while authorization'))

    def create_event(self, start_time, summary, location, description, attendee_email, attendee_email_2, attendee_email_3):
        matches = list(datefinder.find_dates(start_time))
        if len(matches):
            start_time = matches[0]
            end_time = start_time + timedelta(hours=1)
        event = {
            'summary': summary,
            'location': 'Hawally',
            'description': description,
            'start': {
                'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Asia/Kuwait',
            },
            'end': {
                'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Asia/Kuwait',
            },
            'conferenceData': {"createRequest": {"requestId": "sample123", "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
            'attendees': [
                {'email': attendee_email},
                {'email': attendee_email_2},
                {'email': attendee_email_3},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 45},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        sendNotification = True
        return (service.events().insert(calendarId='primary', sendNotifications=sendNotification, body=event, conferenceDataVersion=1).execute())
