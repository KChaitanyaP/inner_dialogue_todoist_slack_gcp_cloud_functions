import json
import pytz
import copy
from datetime import datetime
from datetime_utils import get_today_date_local
from auth_utils import _get_credentials
from google.cloud import bigquery

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def create_activity_edit_modal(text_input):
    activity_id = text_input.split('edit-activity-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details: ", activity_details)
    with open("edit-goal-modal.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    print("edit_goal_template: ", edit_goal_template)
    true = True
    edit_activity_template = copy.deepcopy(edit_goal_template)
    edit_activity_template['title']['text'] = 'Edit Activity'
    edit_activity_template['private_metadata'] = "activity_id:" + str(
        activity_details['step_id']) + ",action:edit-activity"
    edit_activity_template['blocks'] = []
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            block['element']['initial_value'] = activity_details['step_name']
            block['label']['text'] = 'Activity'
            edit_activity_template['blocks'] += [block]
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            block['element']['initial_value'] = activity_details['comments']
            edit_activity_template['blocks'] += [block]
        elif 'block_id' in block.keys():
            if block['block_id'] == 'edit-goal-pretext':
                block['text']['text'] = "Please edit the activity details and add comments"
                edit_activity_template['blocks'] += [block]
    _suggestion_ts = activity_details['suggestion_ts'] if activity_details[
                                                              'suggestion_ts'] != '' else '1990-01-01-08:00:00'
    suggestion_ts_utc = datetime.strptime(_suggestion_ts, "%Y-%m-%d-%H:%M:%S")
    utc_datetime = pytz.utc.localize(suggestion_ts_utc)
    date_string = utc_datetime.strftime("%Y-%m-%d")
    local_timezone = pytz.timezone(tz)
    local_datetime = utc_datetime.astimezone(local_timezone)
    local_time_string = local_datetime.strftime("%H:%M")

    edit_activity_template['blocks'] += [{
        "type": "section",
        "block_id": "activity-date-add-step_id-here",
        "text": {
            "type": "mrkdwn",
            "text": "Pick a date to work on this."
        },
        "accessory": {
            "type": "datepicker",
            "initial_date": f"{date_string}",
            "placeholder": {
                "type": "plain_text",
                "text": "Select a date",
                "emoji": true
            },
            "action_id": "datepicker-action"
        }
    },
        {
            "type": "section",
            "block_id": "activity-time-add-step_id-here",
            "text": {
                "type": "mrkdwn",
                "text": "Pick a time"
            },
            "accessory": {
                "type": "timepicker",
                "initial_time": f"{local_time_string}",
                "timezone": f"{tz}",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": true
                },
                "action_id": "timepicker-action"
            }
        }]

    print("edit_activity_template: ", edit_activity_template)
    return edit_activity_template


def create_activity_archive_modal(text_input, action_type="archive"):
    # type can be finish or archive
    activity_id = text_input.split(f'{action_type}-activity-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details: ", activity_details)
    with open("archive-goal-modal.json", 'r') as json_file:
        archive_goal_template = json.load(json_file)
    print("archive_goal_template: ", archive_goal_template)
    archive_goal_template['private_metadata'] = "activity_id:" + str(
        activity_details['step_id']) + f",action:{action_type}-activity"
    archive_goal_template['title']['text'] = f"{action_type} Activity"
    for idx, block in enumerate(archive_goal_template['blocks']):
        if 'block_id' in block.keys():
            if block['block_id'] == "header-block":
                archive_goal_template['blocks'][idx]['text']['text'] = \
                    f"You are about to *{action_type}* this activity."
            if block['block_id'] == "goal-details-block":
                archive_goal_template['blocks'][idx]['text']['text'] = activity_details['step_name']

    print("archive_task_template: ", archive_goal_template)
    return archive_goal_template


def create_new_activity_modal(task_id):
    true = True
    with open("edit-goal-modal.json", 'r') as json_file:
        create_goal_template = json.load(json_file)
    create_activity_template = copy.deepcopy(create_goal_template)
    create_activity_template['blocks'] = []

    create_activity_template['private_metadata'] = "task_id:" + str(task_id) + ",action:create-activity"
    create_activity_template['title']['text'] = 'Create Activity'

    for idx, block in enumerate(create_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            block['element']['initial_value'] = ''
            block['label']['text'] = 'Activity'
            create_activity_template['blocks'] += [block]
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            block['element']['initial_value'] = ''
            create_activity_template['blocks'] += [block]
        elif 'block_id' in block.keys():
            if block['block_id'] == 'edit-goal-pretext':
                block['text']['text'] = 'Please enter following details to create the new activity.'
                create_activity_template['blocks'] += [block]
    create_activity_template['blocks'] += [{
        "type": "section",
        "block_id": "activity-date-add-step_id-here",
        "text": {
            "type": "mrkdwn",
            "text": "Pick a date to work on this."
        },
        "accessory": {
            "type": "datepicker",
            "initial_date": get_today_date_local(),
            "placeholder": {
                "type": "plain_text",
                "text": "Select a date",
                "emoji": true
            },
            "action_id": "datepicker-action"
        }
    },
        {
            "type": "section",
            "block_id": "activity-time-add-step_id-here",
            "text": {
                "type": "mrkdwn",
                "text": "Pick a time"
            },
            "accessory": {
                "type": "timepicker",
                "initial_time": "11:00",
                "timezone": f"{tz}",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": true
                },
                "action_id": "timepicker-action"
            }
        }]
    print("create_activity_template: ", create_activity_template)
    return create_activity_template
