import json
import os
import copy
import pytz
from datetime import datetime

from google.cloud import storage
from google.cloud import bigquery
from google.oauth2 import service_account

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def _get_credentials():
    credentials = os.environ.get("CREDENTIALS")
    svc = json.loads(credentials.replace("\'", "\""))
    return service_account.Credentials.from_service_account_info(svc)


def submit_activity_create_input(activity_id, task_id, input_data):
    activity_details = {'step_id': str(activity_id), 'task_id': str(task_id),
                        'step_name': input_data['edit-goal-name']['goal-input-action']['value'],
                        'comments': input_data['edit-goal-comments']['comments-input-action']['value']}
    now = datetime.now()
    activity_details['created_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    activity_details['modified_ts'] = ""
    activity_details['finish_mandatory'] = "true"

    suggestion_date = input_data['activity-date-add-step_id-here']['datepicker-action']['selected_date']
    suggestion_time = input_data['activity-time-add-step_id-here']['timepicker-action']['selected_time']
    date_object = datetime.strptime(suggestion_date, "%Y-%m-%d")
    time_object = datetime.strptime(suggestion_time, "%H:%M").time()
    timezone = pytz.timezone(input_data['activity-time-add-step_id-here']['timepicker-action']['timezone'])
    suggestion_ts = datetime.combine(date_object, time_object)
    suggestion_ts_local = timezone.localize(suggestion_ts)
    current_datetime = datetime.now(timezone)
    if suggestion_ts_local <= current_datetime:
        activity_details['suggestion_ts'] = ''
        suggestion_ts_local_msg = ''
    else:
        utc_time = suggestion_ts_local.astimezone(pytz.utc)
        utc_time_str = utc_time.strftime("%Y-%m-%d-%H:%M:%S")
        activity_details['suggestion_ts'] = utc_time_str
        suggestion_ts_local_msg = suggestion_ts_local.strftime("%B-%d-%Y %H:%M")

    activity_details['suggestion_notification_scheduler'] = ""
    activity_details['suggestion_text'] = ""
    activity_details['suggestion_notification_sent'] = ""
    activity_details['estimated_tat'] = ""
    activity_details['retry_suggestion'] = "true"
    activity_details['responded'] = "false"

    client = bigquery.Client(credentials=_get_credentials())
    query = f"SELECT task_name, status FROM `useful-proposal-424218-t8.inner_dialogue_data.tasks` " \
            f"where task_id='{task_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_status = rows[0]['status']
    print("task_status : ", task_status)

    activity_details['status'] = task_status
    print("activity_details_created: ", activity_details)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(activity_details))
    print('saved new task to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        create_goal_template = json.load(json_file)
    create_activity_template = copy.deepcopy(create_goal_template)
    create_activity_template['blocks'] = []

    for idx, block in enumerate(create_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            block['text']['text'] = \
                f"You have successfully created a new activity. All the best! Here are the details:\n" \
                f"*Parent Task:* {rows[0]['task_name']}"
            create_activity_template['blocks'] += [block]
        if block['block_id'] == 'edit_goal_name':
            block['text']['text'] = f"*Task:* {activity_details['step_name']}"
            create_activity_template['blocks'] += [block]
        elif block['block_id'] == 'edit_goal_comments':
            block['text']['text'] = f"*Comments:* {activity_details['comments']}"
            create_activity_template['blocks'] += [block]
    create_activity_template['blocks'] += [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Suggestion timestamp (local timezone):* {suggestion_ts_local_msg}"
        }
    }]
    print("create_activity_template: ", create_activity_template)
    return create_activity_template


def submit_activity_status_update(activity_id, action_type='archive'):
    status = {"archive": "ARCHIVED", "finish": "FINISHED"}
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details previous: ", activity_details)

    activity_details_updated = copy.deepcopy(activity_details)
    activity_details_updated['status'] = status[action_type]
    now = datetime.now()
    activity_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    print("activity_details_updated: ", activity_details_updated)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with blob.open("w") as f:
        f.write(json.dumps(activity_details_updated))
    print('activity data file uploaded to GCS')

    with open("archive-goal-output.json", 'r') as json_file:
        archive_goal_template = json.load(json_file)
    for idx, block in enumerate(archive_goal_template['blocks']):
        if 'block_id' in block.keys():
            if block['block_id'] == 'archive_goal_section':
                archive_goal_template['blocks'][idx]['text']['text'] = \
                    f"You have successfully updated status to {status[action_type]} for the following activity: " \
                    f"*{activity_details_updated['step_name']}*"

    print("archive_goal_template: ", archive_goal_template)
    return archive_goal_template


def submit_activity_edit_input(activity_id, input_data):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details previous: ", activity_details)

    activity_details_updated = copy.deepcopy(activity_details)
    # using the same template as edit-goal so need to refactor to avoid confusion
    activity_details_updated['step_name'] = input_data['edit-goal-name']['goal-input-action']['value']
    activity_details_updated['comments'] = input_data['edit-goal-comments']['comments-input-action']['value']
    now = datetime.now()
    activity_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    suggestion_date = input_data['activity-date-add-step_id-here']['datepicker-action']['selected_date']
    suggestion_time = input_data['activity-time-add-step_id-here']['timepicker-action']['selected_time']
    date_object = datetime.strptime(suggestion_date, "%Y-%m-%d")
    time_object = datetime.strptime(suggestion_time, "%H:%M").time()
    timezone = pytz.timezone(input_data['activity-time-add-step_id-here']['timepicker-action']['timezone'])
    suggestion_ts = datetime.combine(date_object, time_object)
    suggestion_ts_local = timezone.localize(suggestion_ts)
    current_datetime = datetime.now(timezone)
    if suggestion_ts_local <= current_datetime:
        activity_details_updated['suggestion_ts'] = ''
        suggestion_ts_local_msg = ''
    else:
        utc_time = suggestion_ts_local.astimezone(pytz.utc)
        utc_time_str = utc_time.strftime("%Y-%m-%d-%H:%M:%S")
        activity_details_updated['suggestion_ts'] = utc_time_str
        suggestion_ts_local_msg = suggestion_ts_local.strftime("%B-%d-%Y %H:%M")

    print("activity_details_updated: ", activity_details_updated)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(activity_details_updated))
    print('saved edited activity file to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    edit_activity_template = copy.deepcopy(edit_goal_template)

    _suggestion_ts = activity_details['suggestion_ts'] if activity_details[
                                                              'suggestion_ts'] != '' else '1990-01-01-08:00:00'
    suggestion_ts_utc = datetime.strptime(_suggestion_ts, "%Y-%m-%d-%H:%M:%S")
    utc_datetime = pytz.utc.localize(suggestion_ts_utc)
    date_string = utc_datetime.strftime("%B-%d-%Y")
    local_timezone = pytz.timezone(tz)
    local_datetime = utc_datetime.astimezone(local_timezone)
    local_time_string = local_datetime.strftime("%H:%M")

    edit_activity_template['blocks'] = []
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            block['text']['text'] = "You have successfully updated the activity. Here are the update details:"
            edit_activity_template['blocks'] += [block]
        elif block['block_id'] == 'edit_goal_name':
            block['text']['text'] = \
                f"*Activity:*\n`Old`: {activity_details['step_name']}\n`New`: {activity_details_updated['step_name']}"
            edit_activity_template['blocks'] += [block]
        elif block['block_id'] == 'edit_goal_comments':
            block['text']['text'] = \
                f"*Comments:*\n`Old`: {activity_details['comments']}\n`New`: {activity_details_updated['comments']}"
            edit_activity_template['blocks'] += [block]
    edit_activity_template['blocks'] += [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Suggestion timestamp (local timezone):*\n"
                    f"`Old`: {date_string + ' ' + local_time_string}\n"
                    f"`New`: {suggestion_ts_local_msg}"
        }
    }]
    print("edit_activity_template: ", edit_activity_template)
    return edit_activity_template
