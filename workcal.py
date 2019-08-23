import datetime
import pickle
import os.path
from googleapiclient import discovery
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import iso8601
import argparse
from colorama import Style, Fore, Back

parser = argparse.ArgumentParser()
#parser.add_argument('hours', type=float)
parser.add_argument('-range',type=int, default=20)

args = parser.parse_args()

overtime = float(input("Current overtime: "))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server()
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('calendar', 'v3', credentials=creds)
now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
cal_result = service.calendarList().list().execute();
cals = cal_result.get('items',[])
events_result = service.events().list(calendarId='vqskc00l40heih44klssjkkito@group.calendar.google.com', timeMin=now,
                                      maxResults=args.range, singleEvents=True,
                                      orderBy='startTime').execute()
events = events_result.get('items', [])


next_work_dates = []
next_holiday_dates = []

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    end = event['end'].get('dateTime', event['end'].get('date'))
    start_val = iso8601.parse_date(start)
    if event['summary'] == 'Arbeiten':
        end_val = iso8601.parse_date(end)
        duration = end_val - start_val
        next_work_dates.append((start_val, duration))
    elif event['summary'] == 'Urlaub':
        next_holiday_dates.append(start_val)
    else:
        print("Invalid element '{}' found in calendar!".format(event['summary']))


    #duration = end_val-start_val
    #print(duration.seconds/60/60)


def get_time_on_day(date):
    for datet, duration in next_work_dates:
        if datet.date() == date:
            return duration.seconds / 60 / 60
    return 0


def is_holiday_on_day(date):
    return any(datet.date() == date for datet in next_holiday_dates)


def get_pause(hours):
    if hours > 8:
        return 0.75
    elif hours > 6:
        return 0.5
    return 0


# analyze the next days

#overtime = args.hours
weekday_minus = 4

if overtime < 0:
    current_ot_string = f"current overtime: {Fore.RED}{Style.BRIGHT}{overtime}h{Style.RESET_ALL}"
else:
    current_ot_string = f"current overtime: {Style.BRIGHT}{overtime}h{Style.RESET_ALL}"
print(f"\n      {current_ot_string:^50}")
print(f"{Style.DIM}(assuming todays expected time is already subtracted){Style.RESET_ALL}")
print()

last_month = datetime.date.today().month

for date in [datetime.date.today()+datetime.timedelta(days=i) for i in range(args.range)]:
    day = date.strftime("%a")
    work_time = get_time_on_day(date)
    pause_time = get_pause(work_time)

    day_label = ""
    warn_label = ""

    overtime_delta = 0

    if is_holiday_on_day(date):
        # assert work_time == 0 actually this is allowed
        day_label = "HOLIDAY"
    elif work_time > 0:
        day_label = "WORK"

    if work_time - get_pause(work_time) > 10:
        warn_label = "<- exceeded max work time by {:.2f}h!".format(work_time-get_pause(work_time)-10)
        work_time = 10 + get_pause(work_time)

    if 6 < work_time < 7:
        warn_label = "<- losing 30min because of lunch break!"

    overtime_delta = work_time - pause_time

    # TODO add work on holiday
    if date.weekday() < 5 and datetime.date.today() != date and not is_holiday_on_day(date):
        overtime_delta -= weekday_minus

    overtime += overtime_delta

    if last_month != date.month:
        center_text = f" ----- {date.strftime('%B')} -----"
        print(f"\n      {center_text:^42}\n")
        last_month = date.month
    elif date.weekday() == 0:
        print()

    styled_ot_delta = f"{overtime_delta: >+8.2f}"

    if overtime_delta == 0 and not is_holiday_on_day(date):
        styled_prefix = f"{Style.DIM}{date.day:>2}. {day:<3} {day_label:<7}"
    else:
        styled_prefix = f"{date.day:>2}. {day:<3} {day_label:<7}"

        if overtime_delta > 0:
            styled_ot_delta = f"{Fore.GREEN}{overtime_delta: >+8.2f}{Fore.RESET}"
        elif overtime_delta < 0:
            styled_ot_delta = f"{Fore.RED}{overtime_delta: >+8.2f}{Fore.RESET}"

    if work_time > 0:
        styled_work_time = f"{Fore.GREEN}{work_time:>8.2f}{Fore.RESET}"
    else:
        styled_work_time = f"{work_time:>8.2f}"

    if overtime < 0 and overtime_delta != 0:
        styled_ot = f"{Fore.RED}{overtime: >+8.2f}{Fore.RESET}"
    else:
        styled_ot = f"{Fore.WHITE}{overtime: >+8.2f}{Fore.RESET}"

    print(f"      {styled_prefix} {styled_work_time} {styled_ot_delta} {styled_ot}"
          f" {Fore.YELLOW}{warn_label} {Style.RESET_ALL}")

print()