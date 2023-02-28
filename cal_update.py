import datetime
import os.path
from secrets import calendar_name, club_id, gc_id_prefix

from addict import Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import get_strava_data

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarEvent:
    def __init__(self, strava_token, strava_event, service, calendar_id):
        self.strava_token = strava_token
        self.strava_event = Dict(strava_event)
        self.service = service
        self.calendar_id = calendar_id
        self.url = f"https://www.strava.com/clubs/{club_id}/group_events"
        self.event_url = f"{self.url}/{self.strava_event.id}"
        self.strava_route = None
        self.has_route = None
        self.strava_rute_id = None
        self.est_duration = None
        self.desc = None

    def process_entry(self):
        try:
            event_exists = None
            event_exists = (
                self.service.events()
                .get(
                    calendarId=self.calendar_id,
                    eventId=f"{gc_id_prefix}{self.strava_event.id}",
                )
                .execute()
            )
        except HttpError as error:
            if error.status_code == 404:
                print(
                    f"ID:{self.strava_event.id} - No Google Calendar Event, Creating..."
                )
                self.create_update_entry()
            elif error.status_code == 409:
                print(
                    f"ID:{self.strava_event.id} - Google Calendar Event Already Created"
                )
            else:
                print("An error occurred: %s" % error)

        if event_exists and event_exists["status"] == "cancelled":
            print(f"ID:{self.strava_event.id} - Deleted from calendar, recreating...")
            is_deleted = True
            self.create_update_entry(is_deleted)
        elif event_exists:
            print(f"ID:{self.strava_event.id} - Google Calendar Event Already Created")

    def create_update_entry(self, is_deleted=False):
        try:
            self.strava_rute_id = self.strava_event["route"]["id"]
            strava_route = get_strava_data.get_route_data(
                self.strava_rute_id, self.strava_token
            )
            self.strava_route = Dict(strava_route)
            self.est_duration = round((self.strava_route.distance / 1000) / 20 + 1)
            self.has_route = True
            self.create_description()
        except TypeError as error:
            if TypeError:
                print(f"ID:{self.strava_event.id} - No Route for entry")
                self.est_duration = 1
                self.has_route = False
                self.create_description()
            else:
                print(error)

        try:
            # Time
            start_time = self.strava_event.upcoming_occurrences[0].split("Z")[0]
            start_time_obj = datetime.datetime.fromisoformat(start_time)
            end_time_obj = start_time_obj + datetime.timedelta(hours=self.est_duration)
            end_time = end_time_obj.isoformat() + "Z"

            event = {
                "id": f"{gc_id_prefix}{self.strava_event.id}",
                "summary": f"Club Ride: {self.strava_event.title}",
                "location": self.strava_event.address,
                "description": self.desc,
                "start": {
                    "dateTime": self.strava_event.upcoming_occurrences[0],
                    "timeZone": "Europe/London",
                },
                "end": {"dateTime": end_time, "timeZone": "Europe/London"},
            }
            if is_deleted:
                self.service.events().update(
                    calendarId=self.calendar_id,
                    body=event,
                    eventId=f"{gc_id_prefix}{self.strava_event.id}",
                ).execute()
            else:
                self.service.events().insert(
                    calendarId=self.calendar_id, body=event
                ).execute()
            print(f"ID:{self.strava_event.id} - Created Google Calendar Entry")

        except HttpError as error:
            print(f"An error occurred: {error}")

    def create_description(self):
        if self.has_route:
            desc = """{description}

Route Summary:
    Distance: {distance}km
    Elevation: {elevation}m

Strava Event - {url}
""".format(
                description=self.strava_event.description,
                distance=round(self.strava_route.distance / 1000, 2),
                elevation=round(self.strava_route.elevation_gain),
                url=self.event_url,
            )
        else:
            desc = """{description}

Strava Event - {url}
""".format(
                description=self.strava_event.description, url=self.event_url
            )

        self.desc = desc


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Determine Calendar
        print("Getting calendar list...")
        calendar_list = (
            service.calendarList()
            .list(
                syncToken=None,
                minAccessRole=None,
                maxResults=None,
                showDeleted=None,
                showHidden=None,
                pageToken=None,
            )
            .execute()
        )
        cals = calendar_list.get("items", [])

        for cal in cals:
            if cal["summary"] == calendar_name:
                calendar_id = cal["id"]
                print(cal["id"])
                break
    except HttpError as error:
        print(f"An error occurred: {error}")

    strava_token = get_strava_data.renew_token()
    strava_events = get_strava_data.get_events(strava_token)

    for strava_event in strava_events:
        if type(strava_event) == str:
            calerdar_event = CalendarEvent(
                strava_token, strava_events, service, calendar_id
            )
            calerdar_event.process_entry()
            break
        else:
            calerdar_event = CalendarEvent(
                strava_token, strava_event, service, calendar_id
            )
            calerdar_event.process_entry()


if __name__ == "__main__":
    main()
