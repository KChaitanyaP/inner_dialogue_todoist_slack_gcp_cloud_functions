import json
import os
import copy
from datetime import datetime

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

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` " \
            f"where task_id='{task_id}' and status!='FINISHED'"
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
    _frequency = input_data['frequency_select']['frequency_select']['selected_option']['value']
    task_details['frequency'] = _frequency if _frequency != 'null' else "Once"
    print("_frequency: ", task_details['frequency'])
    _auto_create_activities_flag = \
        input_data['auto_activity_creation_select']['auto_activity_creation_select']['selected_option']['value']
    _auto_create_activities_flag = _auto_create_activities_flag if _auto_create_activities_flag != 'null' else "Yes"
    print("_auto_create_activities_flag: ", _auto_create_activities_flag)
    now = datetime.now()
    task_details['created_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    task_details['modified_ts'] = ""

    client = bigquery.Client(credentials=_get_credentials())
    query = f"SELECT goal_name, status FROM `useful-proposal-424218-t8.inner_dialogue_data.goals` " \
            f"where goal_id='{goal_id}'"
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
        if task_details['frequency'] == 'Once':
            print("Code to be done. Take into account: current_date, task_start_date, task_end_date")
    return create_goal_template
