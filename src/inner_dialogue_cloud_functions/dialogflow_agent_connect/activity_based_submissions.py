import json
import copy
import pytz
import uuid
from datetime import datetime, timedelta
from auth_utils import _get_credentials
from google.cloud import storage
from google.cloud import bigquery
from scheduler_utils import create_scheduler_job, update_scheduler_job

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def submit_activity_create_input(activity_id, task_id, input_data):
    activity_details = {'step_id': str(activity_id), 'task_id': str(task_id),
                        'step_name': input_data['edit-goal-name']['goal-input-action']['value'],
                        'comments': input_data['edit-goal-comments']['comments-input-action']['value'],
                        'modified_ts': "", 'finish_mandatory': "true", 'suggestion_text': "",
                        'suggestion_notification_sent': "", 'estimated_tat': "", 'retry_suggestion': "true",
                        'responded': "false"}
    now = datetime.now()
    activity_details['created_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")

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

    client = bigquery.Client(credentials=_get_credentials())
    query = f"SELECT task_name, status FROM `scenic-style-432903-u9.inner_dialogue_data.tasks` " \
            f"where task_id='{task_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_status = rows[0]['status']
    print("task_status : ", task_status)

    activity_details['status'] = task_status
    print("activity_details_created: ", activity_details)

    scheduler_data, cron = prepare_activity_scheduler(activity_details)
    scheduler = create_scheduler_job(scheduler_data, cron)
    activity_details['suggestion_notification_scheduler'] = scheduler['name']

    bucket_name = "id-conversation-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # with blob.open("w") as f:
    #     f.write(json.dumps(activity_details))
    blob.upload_from_string(json.dumps(activity_details))
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

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.steps` where step_id='{activity_id}'"
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

    bucket_name = "id-conversation-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(activity_details_updated))
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


def submit_single_activity_edit_input(activity_id, input_data, action_type='single_update'):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details previous: ", activity_details)

    activity_details_updated = copy.deepcopy(activity_details)
    # using the same template as edit-goal so need to refactor to avoid confusion
    if 'edit-goal-name' in input_data.keys():
        activity_details_updated['step_name'] = input_data['edit-goal-name']['goal-input-action']['value']
    if 'edit-goal-comments' in input_data.keys():
        activity_details_updated['comments'] = input_data['edit-goal-comments']['comments-input-action']['value']
    now = datetime.now()
    activity_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")

    if action_type == 'single_update':
        suggestion_date = input_data['activity-date-add-step_id-here']['datepicker-action']['selected_date']
        suggestion_time = input_data['activity-time-add-step_id-here']['timepicker-action']['selected_time']
    elif action_type == 'auto_update':
        suggestion_date = datetime.strptime(activity_details['suggestion_ts'], '%Y-%m-%d-%H:%M:%S').strftime('%Y-%m-%d')
        suggestion_time = input_data['activity-time-add-step_id-here']['timepicker-action']['selected_time']
    else:
        raise NotImplementedError(f"Not implemented action_type: {action_type}")

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
        if utc_time_str != activity_details['suggestion_ts']:
            activity_details_updated['suggestion_ts'] = utc_time_str
            scheduler_data, cron = prepare_activity_scheduler(activity_details_updated)
            scheduler = update_scheduler_job(activity_details['suggestion_notification_scheduler'],
                                             scheduler_data, cron)
            activity_details_updated['suggestion_notification_scheduler'] = scheduler['name']

        suggestion_ts_local_msg = suggestion_ts_local.strftime("%B-%d-%Y %H:%M")

    print("activity_details_updated: ", activity_details_updated)

    bucket_name = "id-conversation-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not activity_details == activity_details_updated:
        blob.upload_from_string(json.dumps(activity_details_updated))
        print('saved edited activity file to GCS')

    with open("edit-goal-output.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    edit_activity_template = copy.deepcopy(edit_goal_template)
    _suggestion_ts = \
        activity_details['suggestion_ts'] if activity_details['suggestion_ts'] != '' else '1990-01-01-08:00:00'
    suggestion_ts_utc = datetime.strptime(_suggestion_ts, "%Y-%m-%d-%H:%M:%S")
    utc_datetime = pytz.utc.localize(suggestion_ts_utc)
    date_string = utc_datetime.strftime("%B-%d-%Y")
    local_timezone = pytz.timezone(tz)
    local_datetime = utc_datetime.astimezone(local_timezone)
    local_time_string = local_datetime.strftime("%H:%M")

    edit_activity_template['blocks'] = []
    if not activity_details == activity_details_updated:
        for idx, block in enumerate(edit_goal_template['blocks']):
            if block['block_id'] == 'edit_goal_section':
                block['text']['text'] = "You have successfully updated the activity. Here are the update details:"
                edit_activity_template['blocks'] += [block]
            elif block['block_id'] == 'edit_goal_name':
                block['text']['text'] = \
                    f"*Activity:*\n`Old`: " \
                    f"{activity_details['step_name']}\n`New`: {activity_details_updated['step_name']}"
                edit_activity_template['blocks'] += [block]
            elif block['block_id'] == 'edit_goal_comments':
                block['text']['text'] = \
                    f"*Comments:*\n`Old`: " \
                    f"{activity_details['comments']}\n`New`: {activity_details_updated['comments']}"
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
    else:
        for idx, block in enumerate(edit_goal_template['blocks']):
            if block['block_id'] == 'edit_goal_section':
                block['text']['text'] = "No update for activity details as same details are entered."
                edit_activity_template['blocks'] += [block]
    print("edit_activity_template: ", edit_activity_template)
    return edit_activity_template


def submit_activity_edit_input(activity_id, input_data):
    edit_activity_template = submit_single_activity_edit_input(activity_id, input_data)
    _auto_update = input_data['auto-update-suggestion-times-action']['actionId-auto-update-suggestion-times-action']
    if len(_auto_update['selected_options']) > 0:
        keys_to_update = ['activity-time-add-step_id-here']
        print("trying to auto-update-suggestion-times for all activities with future suggestion times")
        client = bigquery.Client(credentials=_get_credentials())
        query = f"""SELECT step_id FROM `scenic-style-432903-u9.inner_dialogue_data.steps` where 
task_id in (select task_id from  `scenic-style-432903-u9.inner_dialogue_data.steps` where step_id='{activity_id}')
and PARSE_TIMESTAMP('%Y-%m-%d-%H:%M:%S', suggestion_ts) > CURRENT_TIMESTAMP()"""
        print("query: ", query)
        query_job = client.query(query)
        result = query_job.result()  # Waits for query to finish
        _activity_ids = [dict(row) for row in result]
        activity_ids = [t for t in _activity_ids if t['step_id'] != activity_id]
        print("activity_ids: ", activity_ids)
        for _id in activity_ids:
            message_for_id = submit_single_activity_edit_input(
                _id['step_id'],
                {key: input_data[key] for key in keys_to_update if key in input_data},
                action_type="auto_update"
            )
            print(_id['step_id'], message_for_id)
        if len(activity_ids) > 0:
            edit_activity_template['blocks'] += [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggestion timestamp auto-updated for {len(activity_ids)} activities:*"
                }}]
    return edit_activity_template


def submit_activity_edit_suggestion_time(activity_id, time_delay):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.steps` where step_id='{activity_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details previous: ", activity_details)

    activity_details_updated = copy.deepcopy(activity_details)
    # using the same template as edit-goal so need to refactor to avoid confusion
    current_utc_time = datetime.now()
    activity_details_updated['modified_ts'] = current_utc_time.strftime("%Y-%m-%d-%H:%M:%S")
    future_utc_time = current_utc_time + timedelta(minutes=time_delay)
    formatted_future_time = future_utc_time.strftime("%Y-%m-%d-%H:%M:%S")
    activity_details_updated['suggestion_ts'] = formatted_future_time

    scheduler_data, cron = prepare_activity_scheduler(activity_details_updated)
    scheduler = update_scheduler_job(activity_details['suggestion_notification_scheduler'],
                                     scheduler_data, cron)
    activity_details_updated['suggestion_notification_scheduler'] = scheduler['name']
    print("activity_details_updated: ", activity_details_updated)

    bucket_name = "id-conversation-data"
    blob_name = f"steps-data/step-{activity_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(json.dumps(activity_details_updated))
    print('saved edited activity file to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    edit_activity_template = copy.deepcopy(edit_goal_template)

    suggestion_ts_utc = datetime.strptime(formatted_future_time, "%Y-%m-%d-%H:%M:%S")
    utc_datetime = pytz.utc.localize(suggestion_ts_utc)
    local_timezone = pytz.timezone(tz)
    local_datetime = utc_datetime.astimezone(local_timezone)
    local_time_string = local_datetime.strftime("%H:%M")

    edit_activity_template['blocks'] = []
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            block['text']['text'] = f"Sure. I will remind you again about {activity_details_updated['step_name']} " \
                                    f"in {time_delay} min at around {local_time_string}"
            edit_activity_template['blocks'] += [block]

    print("edit_activity_template: ", edit_activity_template)
    return edit_activity_template


def create_activities_bulk(task_details, activity_dates, frequency):
    now = datetime.now()
    for i, activity_date in enumerate(activity_dates):
        frequency_marker = {"Once": "Today",
                            "Daily": f"on the day {i + 1}",
                            "Weekly": f"for the week {i + 1}",
                            "Monthly": f"for the month {i + 1}",
                            "Yearly": f"for the year {i + 1}"}
        print(f"trying to create activity for {activity_date}")
        activity_id = uuid.uuid4()
        activity_name = f"Do the task {task_details['task_name']} {frequency_marker[frequency]}"
        activity_comments = "auto-created activity based on task frequency"

        activity_details = {'step_id': str(activity_id), 'task_id': str(task_details['task_id']),
                            'step_name': activity_name, 'comments': activity_comments,
                            'created_ts': now.strftime("%Y-%m-%d-%H:%M:%S"), 'modified_ts': "",
                            'finish_mandatory': "true", 'suggestion_text': "",
                            'suggestion_notification_sent': "", 'estimated_tat': "", 'retry_suggestion': "true",
                            'responded': "false", 'status': task_details['status']}
        suggestion_date = activity_date
        suggestion_time = "10:10"
        date_object = datetime.strptime(suggestion_date.strftime("%Y-%m-%d"), "%Y-%m-%d")
        time_object = datetime.strptime(suggestion_time, "%H:%M").time()
        timezone = pytz.timezone(tz)
        suggestion_ts = datetime.combine(date_object, time_object)
        suggestion_ts_local = timezone.localize(suggestion_ts)
        utc_time = suggestion_ts_local.astimezone(pytz.utc)
        utc_time_str = utc_time.strftime("%Y-%m-%d-%H:%M:%S")
        activity_details['suggestion_ts'] = utc_time_str

        print("activity_details_created: ", activity_details)

        bucket_name = "id-conversation-data"
        blob_name = f"steps-data/step-{activity_id}.json"
        storage_client = storage.Client(credentials=_get_credentials())
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        scheduler_data, cron = prepare_activity_scheduler(activity_details)
        scheduler = create_scheduler_job(scheduler_data, cron)
        activity_details['suggestion_notification_scheduler'] = scheduler['name']

        # with blob.open("w") as f:
        #     f.write(json.dumps(activity_details))
        blob.upload_from_string(json.dumps(activity_details))
        print('saved new task to GCS')
    _date_range = f"{activity_dates[0].strftime('%Y-%m-%d')} and {activity_dates[-1].strftime('%Y-%m-%d')}"
    output_message = {"Once": f"once for {activity_dates[0].strftime('%Y-%m-%d')}",
                      "Daily": f"daily for days between {_date_range}",
                      "Weekly": f"weekly once between {_date_range}",
                      "Monthly": f"monthly once between {_date_range}",
                      "Yearly": f"yearly once between {_date_range}"}
    return output_message[frequency]


def prepare_activity_scheduler(activity_details):
    _scheduler_data = str(activity_details['step_id'])
    dt = datetime.strptime(activity_details['suggestion_ts'], "%Y-%m-%d-%H:%M:%S")
    minute = dt.minute
    hour = dt.hour
    day = dt.day
    month = dt.month
    _cron_expression = f"{minute} {hour} {day} {month} *"

    return _scheduler_data, _cron_expression
