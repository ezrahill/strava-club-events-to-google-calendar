import requests

import secrets


def renew_token():
    # Token Refresh

    try:
        response = requests.post(
            url="https://www.strava.com/oauth/token",
            params={
                "client_id": secrets.client_id,
                "client_secret": secrets.client_secret,
                "refresh_token": secrets.refresh_token,
                "grant_type": "refresh_token",
            }
        )
        print(f'Get Token - Response HTTP Status Code: {response.status_code}')

        return (response.json())['access_token']
    except requests.exceptions.RequestException:
        print('HTTP Request failed')


def get_events(token):
    # Get Club Events

    try:
        response = requests.get(
            url=f"https://www.strava.com/api/v3/clubs/{secrets.club_name}/group_events",
            headers={
                "Authorization": f"Bearer {token}"
            },
        )
        print(
            f'Get Events - Response HTTP Status Code: {response.status_code}')
        events = response.json()
        return events
    except requests.exceptions.RequestException:
        print('HTTP Request failed')


def get_route_data(route_id, token):
    # Get Route

    try:
        response = requests.get(
            url=f"https://www.strava.com/api/v3/routes/{route_id}",
            headers={
                "Authorization": f"Bearer {token}"
            },
        )
        print(f'Get Route - Response HTTP Status Code: {response.status_code}')
        return response.json()
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
