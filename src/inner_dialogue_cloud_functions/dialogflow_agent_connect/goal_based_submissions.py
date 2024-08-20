import json
import copy
from datetime import datetime
from auth_utils import _get_credentials

from google.cloud import storage
from google.cloud import bigquery


tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def submit_goal_edit_input(goal_id, input_data):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.goals` where goal_id='{goal_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_details = rows[0]
    print("goal_details previous: ", goal_details)

    goal_details_updated = copy.deepcopy(goal_details)
    goal_details_updated['goal_name'] = input_data['edit-goal-name']['goal-input-action']['value']
    goal_details_updated['comments'] = input_data['edit-goal-comments']['comments-input-action']['value']
    _selected_start_date = input_data['edit-goal-start-date']['start-date-action']['selected_date']
    goal_details_updated['start_date'] = _selected_start_date if _selected_start_date != '0001-01-01' else ''
    _selected_end_date = input_data['edit-goal-end-date']['end-date-action']['selected_date']
    goal_details_updated['end_date'] = _selected_end_date if _selected_end_date != '0001-01-01' else ''
    now = datetime.now()
    goal_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    print("goal_details_updated: ", goal_details_updated)

    bucket_name = "id-conversation-data"
    blob_name = f"goals-data/goal-{goal_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(goal_details_updated))
    print('saved file to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_name':
            edit_goal_template['blocks'][idx]['text'][
                'text'] = f"*Goal:*\n`Old`: {goal_details['goal_name']}\n`New`: {goal_details_updated['goal_name']}"
        elif block['block_id'] == 'edit_goal_start_date':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*Start date:*\n`Old`: {goal_details['start_date']}\n`New`: {goal_details_updated['start_date']}"
        elif block['block_id'] == 'edit_goal_end_date':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*End date:*\n`Old`: {goal_details['end_date']}\n`New`: {goal_details_updated['end_date']}"
        elif block['block_id'] == 'edit_goal_comments':
            edit_goal_template['blocks'][idx]['text']['text'] = \
                f"*Comments:*\n`Old`: {goal_details['comments']}\n`New`: {goal_details_updated['comments']}"

    print("edit_goal_template: ", edit_goal_template)
    return edit_goal_template


def submit_goal_status_update(goal_id, action_type='archive'):
    status = {"archive": "ARCHIVED", "finish": "FINISHED", "activate": "ACTIVE"}
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.goals` where goal_id='{goal_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_details = rows[0]
    print("goal_details previous: ", goal_details)

    goal_details_updated = copy.deepcopy(goal_details)
    goal_details_updated['status'] = status[action_type]
    now = datetime.now()
    goal_details_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    goal_details_updated['start_date'] = str(goal_details_updated['start_date'])
    goal_details_updated['end_date'] = str(goal_details_updated['end_date'])
    print("goal_details_updated: ", goal_details_updated)

    bucket_name = "id-conversation-data"
    blob_name = f"goals-data/goal-{goal_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with blob.open("w") as f:
        f.write(json.dumps(goal_details_updated))
    print('goal data file to GCS')

    query = (
        f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.tasks` "
        f"where goal_id='{goal_id}' and status!='FINISHED'")
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    tasks = [dict(row) for row in result]
    for task in tasks:
        task_updated = copy.deepcopy(task)
        task_updated['status'] = status[action_type]
        now = datetime.now()
        task_updated['modified_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
        task_updated['start_date'] = str(task_updated['start_date'])
        task_updated['end_date'] = str(task_updated['end_date'])
        blob_name = f"tasks-data/task-{task_updated['task_id']}.json"
        blob = bucket.blob(blob_name)
        with blob.open("w") as f:
            f.write(json.dumps(task_updated))
        print("task previous: ", task, 'task updated: ', task_updated, 'task data file to GCS')

        query = (
            f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.steps` "
            f"where task_id='{task_updated['task_id']}' and status!='FINISHED'")
        print("ACTIVITY QUERY: ", query)
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
                    f"You have successfully updated status to {status[action_type]} for the following goal: " \
                    f"*{goal_details_updated['goal_name']}*\nPlease note that all *unfinished* tasks and " \
                    f"activities associated with this goal are updated as well."

    print("archive_goal_template: ", archive_goal_template)
    return archive_goal_template


def submit_goal_create_input(goal_id, input_data):
    goal_details_updated = {'goal_id': str(goal_id),
                            'goal_name': input_data['edit-goal-name']['goal-input-action']['value'],
                            'comments': input_data['edit-goal-comments']['comments-input-action']['value']}
    _selected_start_date = input_data['edit-goal-start-date']['start-date-action']['selected_date']
    goal_details_updated['start_date'] = _selected_start_date if _selected_start_date != '0001-01-01' else ''
    _selected_end_date = input_data['edit-goal-end-date']['end-date-action']['selected_date']
    goal_details_updated['end_date'] = _selected_end_date if _selected_end_date != '0001-01-01' else ''
    now = datetime.now()
    goal_details_updated['created_ts'] = now.strftime("%Y-%m-%d-%H:%M:%S")
    goal_details_updated['modified_ts'] = ""
    goal_details_updated['status'] = "TBD"
    print("goal_details_created: ", goal_details_updated)

    bucket_name = "id-conversation-data"
    blob_name = f"goals-data/goal-{goal_id}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with blob.open("w") as f:
        f.write(json.dumps(goal_details_updated))
    print('saved file to GCS')
    with open("edit-goal-output.json", 'r') as json_file:
        create_goal_template = json.load(json_file)
    for idx, block in enumerate(create_goal_template['blocks']):
        if block['block_id'] == 'edit_goal_section':
            create_goal_template['blocks'][idx]['text'][
                'text'] = f"You have successfully created a new goal. All the best! Here are the details:"
        if block['block_id'] == 'edit_goal_name':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Goal:* {goal_details_updated['goal_name']}"
        elif block['block_id'] == 'edit_goal_start_date':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Start date:* {goal_details_updated['start_date']}"
        elif block['block_id'] == 'edit_goal_end_date':
            create_goal_template['blocks'][idx]['text']['text'] = f"*End date:* {goal_details_updated['end_date']}"
        elif block['block_id'] == 'edit_goal_comments':
            create_goal_template['blocks'][idx]['text']['text'] = f"*Comments:* {goal_details_updated['comments']}"

    print("create_goal_template: ", create_goal_template)
    return create_goal_template
