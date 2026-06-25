from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta
import pytz

SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)
calendar_id = '12356pradip@gmail.com'

tz = pytz.timezone('Asia/Kolkata')
now = datetime.now(tz)

event = {
    'summary': 'આજની રાશિ: સૂર્ય-કર્ક, ચંદ્ર-તુલા',
    'description': 'એસ્ટ્રો પ્રોગ્રામ દ્વારા અપડેટ.',
    'start': {'dateTime': now.isoformat()},
    'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
}

event = service.events().insert(calendarId=calendar_id, body=event).execute()
print(f'રીમાઇન્ડર સેટ થઈ ગયું છે: {event.get("htmlLink")}')