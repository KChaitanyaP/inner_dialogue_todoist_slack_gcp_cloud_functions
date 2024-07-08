import json
import os
import copy
import pytz
import uuid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from google.cloud import storage
from google.cloud import bigquery
from google.oauth2 import service_account

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def _get_credentials():
    credentials = os.environ.get("CREDENTIALS")
    svc = json.loads(credentials.replace("\'", "\""))
    return service_account.Credentials.from_service_account_info(svc)


def submit_task_edit_input(task_id, input_data):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.tasks` where task_id='{task_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_details = rows[0]
    print("task_details previous: ", task_details)

    task_details_updated = copy.deepcopy(task_details)
    # using the same template as edit-goal so need to refactor to avoid confusion
    task_details_updated['task_name'] = input_data['edit-goal-name']['goal-input-action']['value']
    task_details_updated['comments'] = input_data['edit-goal-comments']['comments-input-action']['value']
    _selected_start_date = input_data['edit-goal-start-date']['start-date-action']['selected_date']
    task_details_updated['start_date'] = _selected_start_date if _selected_start_date != '0001-01-01' else ''
    _selected_end_date = input_data['edit-goal-end-date']['end-date-action']['selected_date']
    task_details_updated['end_date'] = _selected_end_date if _selected_end_date != '0001-01-01' else ''
    _selected_frequency = input_data['frequency_select']['frequency_select']['selected_option']['value']
    task_details_updated['frequency'] = _selected_frequency if _selected_frequency is not None \
        else task_details['frequency']
    now = datetime.now()
    task_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    print("task_details_updated: ", task_details_updated)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"tasks-data/task-{task_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(task_details_updated))
    print('saved file to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    edit_goal_template['blocks'] += [{
        "type": "section",
        "block_id": "edit_task_frequency",
        "text": {
            "type": "mrkdwn",
            "text": f"*Frequency:*\n`Old`: {task_details['frequency']}\n`New`: {task_details_updated['frequency']}"
        }
    }]
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                "You have successfully updated the task. Here are the update details:"
        elif block['block_id'] == 'edit_goal_name':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*Task:*\n`Old`: {task_details['task_name']}\n`New`: {task_details_updated['task_name']}"
        elif block['block_id'] == 'edit_goal_start_date':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*Start date:*\n`Old`: {task_details['start_date']}\n`New`: {task_details_updated['start_date']}"
        elif block['block_id'] == 'edit_goal_end_date':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*End date:*\n`Old`: {task_details['end_date']}\n`New`: {task_details_updated['end_date']}"
        elif block['block_id'] == 'edit_goal_comments':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*Comments:*\n`Old`: {task_details['comments']}\n`New`: {task_details_updated['comments']}"

    print("edit_task_template: ", edit_goal_template)
    return edit_goal_template


def submit_task_status_update(task_id, action_type='archive'):
    status = {"archive": "ARCHIVED", "finish": "FINISHED"}
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.tasks` where task_id='{task_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_details = rows[0]
    print("task_details previous: ", task_details)

    task_details_updated = copy.deepcopy(task_details)
    task_details_updated['status'] = status[action_type]
    now = datetime.now()
    task_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    print("task_details_updated: ", task_details_updated)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"tasks-data/task-{task_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with blob.open("w") as f:
        f.write(json.dumps(task_details_updated))
    print('task data file to GCS')

    query = f"""SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` \
where task_id='{task_id}' and status!='FINISHED'
"""
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    activities = [dict(row) for row in result]

    for activity in activities:
        activity_updated = copy.deepcopy(activity)
        activity_updated['status'] = status[action_type]
        now = datetime.now()
        activity_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
        blob_name = f"steps-data/step-{activity_updated['step_id']}.json"
        blob = bucket.blob(blob_name)
        with blob.open("w") as f:
            f.write(json.dumps(activity_updated))
        print("activity previous: ", activity, 'activity updated: ', activity_updated,
              'activity(step) data file to GCS')

    with open("archive-goal-output.json", 'r') as json_file:
        archive_goal_template = json.load(json_file)
    for idx, block in enumerate(archive_goal_template['blocks']):
        if 'block_id' in block.keys():
            if block['block_id'] == 'archive_goal_section':
                archive_goal_template['blocks'][idx]['text']['text'] = \
                    f"You have successfully updated status to {status[action_type]} for the following task: " \
                    f"*{task_details_updated['task_name']}*\nPlease note that all *unfinished* activities " \
                    f"associated with this task are updated as well."

    print("archive_goal_template: ", archive_goal_template)
    return archive_goal_template


def submit_task_create_input(task_id, goal_id, input_data):
    task_details = {'task_id': str(task_id), 'goal_id': str(goal_id),
                    'task_name': input_data['edit-goal-name']['goal-input-action']['value'],
                    'comments': input_data['edit-goal-comments']['comments-input-action']['value']}
    _selected_start_date = input_data['edit-goal-start-date']['start-date-action']['selected_date']
    task_details['start_date'] = _selected_start_date if _selected_start_date != '0001-01-01' else ''
    _selected_end_date = input_data['edit-goal-end-date']['end-date-action']['selected_date']
    task_details['end_date'] = _selected_end_date if _selected_end_date != '0001-01-01' else ''
    _frequency = input_data['frequency_select']['frequency_select']['selected_option']
    task_details['frequency'] = _frequency['value'] if _frequency is not None else "Once"
    print("_frequency: ", task_details['frequency'])
    temp = input_data['auto_activity_creation_select']['auto_activity_creation_select']['selected_option']
    _auto_create_activities_flag = temp['value'] if temp is not None else "Yes"
    print("_auto_create_activities_flag: ", _auto_create_activities_flag)
    now = datetime.now()
    task_details['created_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    task_details['modified_ts'] = ""

    client = bigquery.Client(credentials=_get_credentials())
    query = f"""SELECT goal_name, status FROM `useful-proposal-424218-t8.inner_dialogue_data.goals` \
where goal_id='{goal_id}'
"""
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_status = rows[0]['status']
    print("goal_status : ", goal_status)

    task_details['status'] = goal_status
    print("task_details_created: ", task_details)

    bucket_name = "inner-dialogue-conv-data"
    blob_name = f"tasks-data/task-{task_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(task_details))
    print('saved new task to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        create_goal_template = json.load(json_file)
    create_goal_template['blocks'] += [{
        "type": "section",
        "block_id": "task_frequency",
        "text": {
            "type": "mrkdwn",
            "text": f"*Frequency:* {task_details['frequency']}"
        }
    }]
    for idx, block in enumerate(create_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            create_goal_template['blocks'][idx]['text'][
                'text'] = f"You have successfully created a new task. All the best! Here are the details:\n*" \
                          f"Parent Goal:* {rows[0]['goal_name']}"
        if block['block_id'] == 'edit_goal_name':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Task:* {task_details['task_name']}"
        elif block['block_id'] == 'edit_goal_start_date':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Start date:* {task_details['start_date']}"
        elif block['block_id'] == 'edit_goal_end_date':
            create_goal_template['blocks'][idx]['text']['text'] = f"*End date:* {task_details['end_date']}"
        elif block['block_id'] == 'edit_goal_comments':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Comments:* {task_details['comments']}"

    print("create_task_template: ", create_goal_template)
    if _auto_create_activities_flag == 'Yes':
        print('attempting to create Activities based on frequency')
        if validate_task_date(task_details) and validate_task_date(task_details, 'end_date'):
            _activity_suggestion_dates = get_activity_suggestion_dates(task_details, task_details['frequency'])
            create_bulk_msg = create_activities_bulk(task_details, _activity_suggestion_dates,
                                                     task_details['frequency'])
            create_goal_template['blocks'] += [{
                "type": "section",
                "block_id": "auto-created-activities",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Auto-created Activities* {create_bulk_msg}. Feel free to edit them as you see fit."
                }
            }]
        else:
            print("Seems task dates are not valid. Aborting to create any activities.")
    else:
        print('NOT attempting to create Activities based on frequency as _auto_create_activities_flag=No')
    return create_goal_template


def get_activity_suggestion_dates(task_details, frequency):
    if frequency == 'Once':
        return [task_details['start_date']]
    elif frequency == 'Daily':
        return get_dates_timedelta(task_details['start_date'], task_details['end_date'], frequency)
    elif frequency == 'Weekly':
        return get_dates_timedelta(task_details['start_date'], task_details['end_date'], frequency)
    elif frequency == 'Monthly':
        return get_dates_relativedelta(task_details['start_date'], task_details['end_date'], frequency)
    elif frequency == 'Yearly':
        return get_dates_relativedelta(task_details['start_date'], task_details['end_date'], frequency)
    else:
        print(f"Unrecognised Frequency: {frequency}")


def validate_task_date(task_details, date_key='start_date'):
    _date = task_details[date_key] if task_details[date_key] != '' else '1900-01-01'
    _time = "00:01"
    date_object = datetime.strptime(_date, "%Y-%m-%d")
    time_object = datetime.strptime(_time, "%H:%M").time()
    timezone = pytz.timezone(tz)
    task_ts = datetime.combine(date_object, time_object)
    task_ts_local = timezone.localize(task_ts)
    current_datetime = datetime.now(timezone)
    if task_ts_local < current_datetime:
        return False
    elif date_key == 'end_date':
        start_date = task_details['start_date'] if task_details['start_date'] != '' else '1900-01-01'
        date_object = datetime.strptime(start_date, "%Y-%m-%d")
        task_ts_start = datetime.combine(date_object, time_object)
        task_ts_start_local = timezone.localize(task_ts_start)
        if task_ts_start_local > task_ts_local:
            return False
        else:
            return True
    else:
        return True


def get_dates_relativedelta(start_date, end_date, frequency='Monthly'):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        if frequency == 'Monthly':
            current_date += relativedelta(months=1)
        elif frequency == 'Yearly':
            current_date += relativedelta(years=1)
    return dates


def get_dates_timedelta(start_date, end_date, frequency='Daily'):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []

    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        if frequency == 'Daily':
            current_date += timedelta(days=1)
        elif frequency == 'Weekly':
            current_date += timedelta(weeks=1)

    return dates


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
                            'finish_mandatory': "true", 'suggestion_notification_scheduler': "", 'suggestion_text': "",
                            'suggestion_notification_sent': "", 'estimated_tat': "", 'retry_suggestion': "true",
                            'responded': "false", 'status': task_details['status']}
        suggestion_date = activity_date
        suggestion_time = "10:10"
        date_object = datetime.strptime(suggestion_date, "%Y-%m-%d")
        time_object = datetime.strptime(suggestion_time, "%H:%M").time()
        timezone = pytz.timezone(tz)
        suggestion_ts = datetime.combine(date_object, time_object)
        suggestion_ts_local = timezone.localize(suggestion_ts)
        utc_time = suggestion_ts_local.astimezone(pytz.utc)
        utc_time_str = utc_time.strftime("%Y-%m-%d-%H:%M:%S")
        activity_details['suggestion_ts'] = utc_time_str

        print("activity_details_created: ", activity_details)

        bucket_name = "inner-dialogue-conv-data"
        blob_name = f"steps-data/step-{activity_id}.json"
        storage_client = storage.Client(credentials=_get_credentials())
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        with blob.open("w") as f:
            f.write(json.dumps(activity_details))
        print('saved new task to GCS')

    output_message = {"Once": "once for {activity_dates[0]}",
                      "Daily": f"daily for days between {activity_dates[0]} and {activity_dates[-1]}",
                      "Weekly": f"weekly once between {activity_dates[0]} and {activity_dates[-1]}",
                      "Monthly": f"monthly once between {activity_dates[0]} and {activity_dates[-1]}",
                      "Yearly": f"yearly once between {activity_dates[0]} and {activity_dates[-1]}"}
    return output_message[frequency]
