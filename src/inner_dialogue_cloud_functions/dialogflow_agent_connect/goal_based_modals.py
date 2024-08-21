import json

from google.cloud import bigquery
from auth_utils import _get_credentials


def get_task_list_block(row):
    true = True
    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{row['task_name']}*"
        },
        "accessory": {
            "type": "overflow",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":task-icon: Show Activities",
                        "emoji": true
                    },
                    "value": f"view-task-activities-{row['task_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":pencil: Edit",
                        "emoji": true
                    },
                    "value": f"edit-task-{row['task_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: Mark as Finished",
                        "emoji": true
                    },
                    "value": f"finish-task-{row['task_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":x: Archive",
                        "emoji": true
                    },
                    "value": f"archive-task-{row['task_id']}"
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
                    "text": f"Frequency: {row['frequency']}"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]


def get_goal_list_block(row):
    true = True
    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{row['goal_name']}*"
        },
        "accessory": {
            "type": "overflow",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":task-icon: Show Tasks",
                        "emoji": true
                    },
                    "value": f"view-goal-tasks-{row['goal_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":pencil: Edit",
                        "emoji": true
                    },
                    "value": f"edit-goal-{row['goal_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":woman-running: Activate",
                        "emoji": true
                    },
                    "value": f"activate-goal-{row['goal_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: Mark as Finished",
                        "emoji": true
                    },
                    "value": f"finish-goal-{row['goal_id']}"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": ":x: Archive",
                        "emoji": true
                    },
                    "value": f"archive-goal-{row['goal_id']}"
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
                }
            ]
        },
        {
            "type": "divider"
        }
    ]


def goals_comments_list():
    client = bigquery.Client(credentials=_get_credentials())

    query = 'SELECT goal_id, goal_name, comments FROM `scenic-style-432903-u9.inner_dialogue_data.goals`'
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    return rows


def create_goals_list_modal():
    client = bigquery.Client(credentials=_get_credentials())

    query = 'SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.goals`'
    print("QUERY: ", query)
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
            "text": "List of Goals",
            "emoji": true
        },
        "blocks": []
    }
    _blocks = []
    for row in rows:
        print("row: ", row)
        _blocks += get_goal_list_block(row)
    _blocks += [
        {
            "type": "actions",
            "block_id": "add-new-goal-button",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add New Goal",
                        "emoji": true
                    },
                    "value": "create_new_goal",
                    "style": "primary",
                    "action_id": "create_new_goal_action"
                }
            ]
        }
    ]
    _modal['blocks'] = _blocks
    print("_modal: ", _modal)
    return _modal


def goal_tasks_comments_list(goal_id):
    client = bigquery.Client(credentials=_get_credentials())

    query = f"""SELECT task_id, task_name, comments FROM `scenic-style-432903-u9.inner_dialogue_data.tasks` 
where goal_id='{goal_id}'"""
    print("goal_tasks_comments_list QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    return rows


def create_view_goal_tasks_modal(text_input):
    goal_id = text_input.split('view-goal-tasks-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.tasks` where goal_id='{goal_id}'"
    print("create_view_goal_tasks_modal query: ", query)
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
            "text": "List of Tasks",
            "emoji": true
        },
        "blocks": []
    }
    _blocks = []
    for row in rows:
        print("row: ", row)
        _blocks += get_task_list_block(row)
    _blocks += [
        {
            "type": "actions",
            "block_id": "add-new-task-button",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add New Task",
                        "emoji": true
                    },
                    "value": "create_new_task",
                    "style": "primary",
                    "action_id": f"create_new_task_goal-id:{goal_id}"
                }
            ]
        }
    ]
    _modal['blocks'] = _blocks
    print("_modal: ", _modal)
    return _modal


def create_goal_edit_modal(text_input):
    goal_id = text_input.split('edit-goal-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.goals` where goal_id='{goal_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_details = rows[0]
    print("goal_details: ", goal_details)
    with open("edit-goal-modal.json", 'r') as json_file:
        edit_goal_template = json.load(json_file)
    print("edit_goal_template: ", edit_goal_template)
    edit_goal_template['private_metadata'] = "goal_id:" + str(goal_details['goal_id']) + ",action:edit-goal"
    for idx, block in enumerate(edit_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            edit_goal_template['blocks'][idx]['element']['initial_value'] = goal_details['goal_name']
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            edit_goal_template['blocks'][idx]['element']['initial_value'] = goal_details['comments']
        elif block['type'] == 'input' and block['element']['action_id'] == 'start-date-action':
            edit_goal_template['blocks'][idx]['element']['initial_date'] = \
                goal_details['start_date'] if goal_details['start_date'] != '' else "0001-01-01"
        elif block['type'] == 'input' and block['element']['action_id'] == 'end-date-action':
            edit_goal_template['blocks'][idx]['element']['initial_date'] = \
                goal_details['end_date'] if goal_details['end_date'] != '' else "0001-01-01"

    print("edit_goal_template: ", edit_goal_template)
    return edit_goal_template


def create_goal_archive_modal(text_input, action_type="archive"):
    # type can be finish or archive
    goal_id = text_input.split(f'{action_type}-goal-', 1)[-1]
    client = bigquery.Client(credentials=_get_credentials())

    query = f"SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.goals` where goal_id='{goal_id}'"
    print("QUERY: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    goal_details = rows[0]
    print("goal_details: ", goal_details)
    with open("archive-goal-modal.json", 'r') as json_file:
        archive_goal_template = json.load(json_file)
    print("archive_goal_template: ", archive_goal_template)
    archive_goal_template['private_metadata'] = \
        "goal_id:" + str(goal_details['goal_id']) + f",action:{action_type}-goal"
    archive_goal_template['title']['text'] = f"{action_type} Goal"
    for idx, block in enumerate(archive_goal_template['blocks']):
        if 'block_id' in block.keys():
            if block['block_id'] == "header-block":
                archive_goal_template['blocks'][idx]['text']['text'] = \
                    f"You are about to *{action_type}* this goal. " \
                    f"Please note that all *unfinished* tasks and activities associated with " \
                    f"this goal would be automatically set to this status."
            if block['block_id'] == "goal-details-block":
                archive_goal_template['blocks'][idx]['text']['text'] = goal_details['goal_name']

    print("archive_goal_template: ", archive_goal_template)
    return archive_goal_template


def create_new_goal_modal():
    with open("edit-goal-modal.json", 'r') as json_file:
        create_goal_template = json.load(json_file)
    create_goal_template['private_metadata'] = "action:create-goal"
    for idx, block in enumerate(create_goal_template['blocks']):
        if block['type'] == 'input' and block['element']['action_id'] == 'goal-input-action':
            create_goal_template['blocks'][idx]['element']['initial_value'] = ''
        elif block['type'] == 'input' and block['element']['action_id'] == 'comments-input-action':
            create_goal_template['blocks'][idx]['element']['initial_value'] = ''
        elif block['type'] == 'input' and block['element']['action_id'] == 'start-date-action':
            create_goal_template['blocks'][idx]['element']['initial_date'] = "0001-01-01"
        elif block['type'] == 'input' and block['element']['action_id'] == 'end-date-action':
            create_goal_template['blocks'][idx]['element']['initial_date'] = "0001-01-01"

    print("create_goal_template: ", create_goal_template)
    return create_goal_template
