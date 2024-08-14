import json
from auth_utils import _get_credentials
import pytz
from datetime import datetime
from datetime_utils import get_today_date_local
from google.cloud import bigquery

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def get_activity_list_block(row):
    _finish_mandatory = 'Yes' if row['finish_mandatory'] else 'No'
    _suggestion_ts = row['suggestion_ts'] if row['suggestion_ts'] != '' else '1990-01-01-08:00:00'
    suggestion_ts_utc = datetime.strptime(_suggestion_ts, "%Y-%m-%d-%H:%M:%S")
    utc_datetime = pytz.utc.localize(suggestion_ts_utc)
    local_timezone = pytz.timezone(tz)
    local_datetime = utc_datetime.astimezone(local_timezone)
    current_datetime = datetime.now(local_timezone)
    if local_datetime <= current_datetime:
        next_suggestion_ts = '-'
    else:
        next_suggestion_ts = local_datetime.strftime("%B-%d-%Y %H:%M")

    true = True
    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{row['step_name']}*"
        },
        "accessory": {
            "type": "overflow",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":pencil: Edit",
                        "emoji": true
                    },
                    "value": f"edit-activity-{row['step_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: Mark as Finished",
                        "emoji": true
                    },
                    "value": f"finish-activity-{row['step_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":x: Archive",
                        "emoji": true
                    },
                    "value": f"archive-activity-{row['step_id']}"
                }
            ]
        }
    },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Current Status: {row['status']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"Mandatory: {_finish_mandatory}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"Next suggestion at: {next_suggestion_ts}"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]


def create_view_task_activities_modal(text_input):
    task_id = text_input.split('view-task-activities-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` where task_id='{task_id}'"
    print("create_view_task_activities_modal QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    true = True
    _modal = {
        "type": "modal",
        "clear_on_close": true,
        "submit": {
            "type": "plain_text",
            "text": "Ok",
            "emoji": true
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": true
        },
        "title": {
            "type": "plain_text",
            "text": "List of Activities",
            "emoji": true
        },
        "blocks": []
    }
    _blocks = []
    for row in rows:
        print("row: ", row)
        _blocks += get_activity_list_block(row)
    _blocks += [
        {
            "type": "actions",
            "block_id": "add-new-activity-button",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add New Activity",
                        "emoji": true
                    },
                    "value": "create_new_activity",
                    "style": "primary",
                    "action_id": f"create_new_activity_task-id:{task_id}"
                }
            ]
        }
    ]
    _modal['blocks'] = _blocks
    print("_modal: ", _modal)
    return _modal


def create_task_archive_modal(text_input, action_type="archive"):
    # type can be finish or archive
    task_id = text_input.split(f'{action_type}-task-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.tasks` where task_id='{task_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_details = rows[0]
    print("task_details: ", task_details)
    with open("archive-goal-modal.json", 'r') as json_file:
        archive_goal_template = json.load(json_file)
    print("archive_goal_template: ", archive_goal_template)
    archive_goal_template['private_metadata'] = "task_id:" + \
                                                str(task_details['task_id']) + f",action:{action_type}-task"
    archive_goal_template['title']['text'] = f"{action_type} Task"
    for idx, block in enumerate(archive_goal_template['blocks']):
        if 'block_id' in block.keys():
            if block['block_id'] == "header-block":
                archive_goal_template['blocks'][idx]['text'][
                    'text'] = f"You are about to *{action_type}* this task. " \
                              f"Please note that all *unfinished* activities " \
                              f"associated with this task would be automatically set to this status."
            if block['block_id'] == "goal-details-block":
                archive_goal_template['blocks'][idx]['text']['text'] = task_details['task_name']

    print("archive_task_template: ", archive_goal_template)
    return archive_goal_template


def create_task_edit_modal(text_input):
    task_id = text_input.split('edit-task-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.tasks` where task_id='{task_id}'"
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    task_details = rows[0]
    print("task_details: ", task_details)
    with open("edit-goal-modal.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    print("edit_goal_template: ", edit_goal_template)
    true = True
    edit_goal_template['title']['text'] = 'Edit Task'
    edit_goal_template['private_metadata'] = "task_id:" + str(task_details['task_id']) + ",action:edit-task"
    edit_goal_template['blocks'] += [{
        "type": "section",
        "block_id": "frequency_select",
        "text": {
            "type": "mrkdwn",
            "text": "*Frequency*"
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": f"{task_details['frequency']}",
                "emoji": true
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Once",
                        "emoji": true
                    },
                    "value": "Once"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Daily",
                        "emoji": true
                    },
                    "value": "Daily"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Weekly",
                        "emoji": true
                    },
                    "value": "Weekly"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Monthly",
                        "emoji": true
                    },
                    "value": "Monthly"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Yearly",
                        "emoji": true
                    },
                    "value": "Yearly"
                }
            ],
            "action_id": "frequency_select"
        }
    }]
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            edit_goal_template['blocks'][idx]['element']['initial_value'] = task_details['task_name']
            edit_goal_template['blocks'][idx]['label']['text'] = 'Task'
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            edit_goal_template['blocks'][idx]['element']['initial_value'] = task_details['comments']
        elif block['type'] == 'input' and block['element']['action_id'] == 'start-date-action':
            edit_goal_template['blocks'][idx]['element']['initial_date'] = \
                task_details['start_date'] if task_details['start_date'] != '' else "0001-01-01"
        elif block['type'] == 'input' and block['element']['action_id'] == 'end-date-action':
            edit_goal_template['blocks'][idx]['element']['initial_date'] = \
                task_details['end_date'] if task_details['end_date'] != '' else "0001-01-01"
        elif 'block_id' in block.keys():
            if block['block_id'] == 'edit-goal-pretext':
                edit_goal_template['blocks'][idx]['text'][
                    'text'] = "Please edit the task details, start date, end date, frequency and add comments"

    print("edit_task_template: ", edit_goal_template)
    return edit_goal_template


def create_new_task_modal(goal_id):
    true = True
    with open("edit-goal-modal.json", 'r') as json_file:
        create_goal_template = json.load(json_file)

    client = bigquery.Client(credentials=_get_credentials())
    _query = f"SELECT * FROM `useful-proposal-424218-t8.inner_dialogue_data.goals` where goal_id='{goal_id}'"

    print("QUERY: ", _query)
    query_job = client.query(_query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_start_date = rows[0]['start_date']
    goal_end_date = rows[0]['end_date']

    create_goal_template['private_metadata'] = "goal_id:" + str(goal_id) + ",action:create-task"
    create_goal_template['title']['text'] = 'Create Task'
    create_goal_template['blocks'] += [{
        "type": "section",
        "block_id": "frequency_select",
        "text": {
            "type": "mrkdwn",
            "text": "*Frequency*"
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Once",
                "emoji": true
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Once",
                        "emoji": true
                    },
                    "value": "Once"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Daily",
                        "emoji": true
                    },
                    "value": "Daily"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Weekly",
                        "emoji": true
                    },
                    "value": "Weekly"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Monthly",
                        "emoji": true
                    },
                    "value": "Monthly"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Yearly",
                        "emoji": true
                    },
                    "value": "Yearly"
                }
            ],
            "action_id": "frequency_select"
        }
    }]

    create_goal_template['blocks'] += [{
        "type": "section",
        "block_id": "auto_activity_creation_select",
        "text": {
            "type": "mrkdwn",
            "text": "*Auto-create Activities based on frequency?*"
        },
        "accessory": {
            "type": "static_select",
            "placeholder": {
                "type": "plain_text",
                "text": "Yes",
                "emoji": true
            },
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "Yes",
                        "emoji": true
                    },
                    "value": "Yes"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                        "emoji": true
                    },
                    "value": "No"
                }
            ],
            "action_id": "auto_activity_creation_select"
        }
    }]

    for idx, block in enumerate(create_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            create_goal_template['blocks'][idx]['element']['initial_value'] = ''
            create_goal_template['blocks'][idx]['label']['text'] = 'Task'
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            create_goal_template['blocks'][idx]['element']['initial_value'] = ''
        elif block['type'] == 'input' and block['element']['action_id'] == 'start-date-action':
            create_goal_template['blocks'][idx]['element']['initial_date'] = get_today_date_local()
        elif block['type'] == 'input' and block['element']['action_id'] == 'end-date-action':
            create_goal_template['blocks'][idx]['element']['initial_date'] = \
                goal_end_date if str(goal_end_date) != '' else "0001-01-01"
        elif 'block_id' in block.keys():
            if block['block_id'] == 'edit-goal-pretext':
                create_goal_template['blocks'][idx]['text']['text'] = \
                    'Please enter following details to create the new task.'

    print("create_task_template: ", create_goal_template)
    return create_goal_template
