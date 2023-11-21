#!/usr/bin/env python3
import json
import os   
import requests

webex_bot_token=os.getenv('webex_bot_token')
pagerduty_api_key=os.getenv('pagerduty_api_key')
webex_room_id="*****"
pagerduty_schedule_ids = "*****"
pagerduty_url = 'https://api.pagerduty.com/oncalls'
webex_url = f'https://webexapis.com/v1/rooms/{webex_room_id}'

def get_oncall_pagerduty_user():
    """
    Retrieve the on-call engineer's email from PagerDuty.

    Returns:
        str: The on-call engineer's email.
    """
    schedule_ids = pagerduty_schedule_ids.split(",")
    users = []
    for schedule_id in schedule_ids:
        userApiUrls = set()
        headers = {
            'Accept': 'application/vnd.pagerduty+json;version=2',
            'Authorization': f'Token token={pagerduty_api_key}'
        }
        payload = {
            'schedule_ids[]': schedule_id,
            'time_zone': 'UTC'
        }
        r = requests.get(pagerduty_url, headers=headers, params=payload)

        if r.status_code != 200:
            return {
                'statusCode': 500,
                'body': json.dumps(f'Failed to retrieve current schedule {schedule_id}')
            }

        response = r.json()
        if 'oncalls' in response:
            for oncall in response['oncalls']:
                userApiUrl = oncall.get('user', {}).get('self')
                userApiUrls.add(userApiUrl)

        if len(userApiUrls):
            userApiUrl = userApiUrls.pop()
            headers = {
                'Accept': 'application/vnd.pagerduty+json;version=2',
                'Authorization': f'Token token={pagerduty_api_key}'
            }
            r = requests.get(userApiUrl, headers=headers)
            if r.status_code != 200:
                return {
                    'statusCode': 500,
                    'body': json.dumps(f'Failed to retrieve current user for schedule {schedule_id}')
                }

        response = r.json()
        user = response.get('user', {}).get('email')
        if user is None:
            return {
                'statusCode': 500,
                'body': json.dumps(f'Failed to retrieve current user for schedule {schedule_id}')
            }

        user = user.rsplit('@', 1)[0]
        users.append(user)
        return user

def make_new_webex_title(pattern, users):
    """
    Format the Webex room title using the specified pattern and on-call engineer's email.

    Args:
        pattern (str): The title pattern with a placeholder for the on-call engineer's email.
        users (str): The on-call engineer's email.

    Returns:
        str: The formatted Webex room title.
    """
    return pattern.format(users=users)

def get_old_webex_title():
    """
    Retrieve the current title of the Webex room.

    Returns:
        str: The current title of the Webex room.
    """
    headers = {'Authorization': f'Bearer {webex_bot_token}'}
    r = requests.get(webex_url, headers=headers)
    response = r.json()
    if r.status_code != 200:
        return {
            'statusCode': 500,
            'body': json.dumps(response.get('message', 'Could not read room'))
        }
    old_webex_title = response.get('title')
    return old_webex_title

def compare_webex_titles(new_title, old_title):
    """
    Compare the new and old Webex titles.

    Args:
        new_title (str): The new Webex title.
        old_title (str): The old Webex title.

    Returns:
        bool: True if titles are the same, False otherwise.
    """
    return new_title == old_title

def put_new_webex_title():
    """
    Update the Webex room title with the new on-call engineer's email.
    """
    webex_title_pattern = f'sre.team : on-call engineer is {get_oncall_pagerduty_user()}@org.com'
    try:
        new_webex_title = make_new_webex_title(webex_title_pattern, get_oncall_pagerduty_user())
    except IndexError as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'{e} for {webex_title_pattern}')
        }

    old_webex_title = get_old_webex_title()

    if compare_webex_titles(new_webex_title, old_webex_title):
        return {'message': 'Webex titles are the same. No update needed.'}

    headers = {
        'Authorization': 'Bearer {}'.format(webex_bot_token)
    }
    payload = {'title': new_webex_title}
    r = requests.put(webex_url, headers=headers, json=payload)
    print(r.content)
    if r.status_code != 200:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Could not modify room title for {webex_room_id}')
        }

    return {}

if __name__ == "__main__":
    put_new_webex_title()
