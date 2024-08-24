# Copyright 2018 Google LLC.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START functions_slack_setup]

from flask import jsonify, make_response
import functions_framework
from slack.signature import SignatureVerifier
from slack_sdk import WebClient
from googleapiclient import discovery
from goal_based_modals import *
from task_based_modals import *
from activity_based_modals import *
from goal_based_submissions import *
from task_based_submissions import *
from activity_based_submissions import *
from auth_utils import _get_credentials
import os

# preventing infinite looping due to slack text invocations, using global variables caching for cloud function
# temporary fix as the behaviour is not guaranteed, we will go with GCS saves shortly
slack_message_text = ""
tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


# [START functions_verify_webhook]
def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ["SLACK_SECRET"])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError("Invalid request/credentials.")


def get_agents_list(service, parent):
    agents = service.projects().locations().agents()
    agents_list = agents.list(parent=parent).execute()
    print("agents_list: ", agents_list)


def get_flows_list(service, parent):
    flows = service.projects().locations().agents().flows()
    flows_list = flows.list(parent=parent).execute()
    print("flows_list: ", flows_list)


def get_fulfillment(service, parent, match_intent_body):
    session = service.projects().locations().agents().sessions()

    match_intent = session.matchIntent(session=parent, body=match_intent_body).execute()
    print("match_intent: ", match_intent)
    fulfill_intent_body = {
        "match": match_intent['matches'][0],
        "matchIntentRequest": match_intent_body
    }

    fulfillment = session.fulfillIntent(session=parent, body=fulfill_intent_body).execute()
    print("fulfillment: ", fulfillment)
    return fulfillment


def create_session_id():
    return uuid.uuid4()


def get_dialogflow_inputs(dialogflow_input):
    gcp_project = "scenic-style-432903-u9"  # os.environ.get("GCP_PROJECT")
    gcp_region = "global"  # os.environ.get("GCP_REGION")
    agent_id = "30135921-1873-4c51-98b3-182f61591063"

    service = discovery.build(
        "dialogflow", "v3", credentials=_get_credentials()
    )
    # get_agents_list(service, loc_parent)
    # get_flows_list(service, f"projects/{gcp_project}/locations/{gcp_region}/agents/{agent_id}")

    session_id = f"projects/{gcp_project}/locations/{gcp_region}/agents/{agent_id}/sessions/{create_session_id()}"
    print("session_id", session_id)
    user_input = {
        "languageCode": "en",
        "text": {"text": dialogflow_input}
    }
    match_intent_body = {
        "persistParameterChanges": False,
        "queryInput": user_input,
        "queryParams": {}
    }

    return service, session_id, match_intent_body


def get_session_id_block(session_id):
    return [{
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"session id:`{session_id.rsplit('/', 1)[-1]}`"
            }
        ]
    }]


def get_slack_response(session_id, dialogflowcx_response, prepend_session_id=True, action_type=None):
    slack_args = {'text': '', 'session_id_block': [], 'blocks': [], 'modal': {}}
    if prepend_session_id:
        slack_args['session_id_block'] = get_session_id_block(session_id)
    if action_type == 'direct_modal':
        slack_args['modal'] = dialogflowcx_response
        return slack_args
    if action_type == 'submission_notification':
        slack_args['blocks'] = dialogflowcx_response['blocks']
        return slack_args
    for response_message in dialogflowcx_response['queryResult']['responseMessages']:
        if 'text' in response_message.keys():
            slack_args['text'] = response_message['text']['text'][0]  # need to check [1] and more?
        elif 'payload' in response_message.keys():
            # it's probably an actions output or modal output
            if 'type' in response_message['payload'].keys():
                if response_message['payload']['type'] == 'modal':
                    slack_args['modal'] = response_message['payload']
            else:
                slack_args['blocks'] = response_message['payload']['blocks']
        else:
            pass
    return slack_args


def send_slack_response(slack_response, trigger_id=None, **kwargs):
    client = WebClient(token=os.environ['SLACK_OAUTH_TOKEN'])
    channel_id = 'D075T6SAUBD'
    if slack_response['session_id_block']:
        print("trying to chat_postMessage: ", slack_response['session_id_block'])
        client.chat_postMessage(channel=channel_id, blocks=slack_response['session_id_block'])
    if slack_response['text'] != '':
        print("trying to text: ", slack_response['text'])
        client.chat_postMessage(channel=channel_id, text=slack_response['text'])
    if slack_response['blocks']:
        print("trying to blocks: ", slack_response['blocks'])
        client.chat_postMessage(channel=channel_id, blocks=slack_response['blocks'])
    if not (not slack_response['modal']):
        if 'view_id' in kwargs.keys():
            print("trying to update modal with ID: ", kwargs['view_id'])
            client.views_update(view=slack_response['modal'], view_id=kwargs['view_id'])
        else:
            print("trying to create new modal: ", slack_response['modal'])
            client.views_open(trigger_id=trigger_id, view=slack_response['modal'])


def send_gcs_dialogflow_input(session_id, timestamp, dialogflow_input):
    bucket_name = "id-conversation-data"
    blob_name = f"dialogflow_input/{session_id}-{timestamp}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(json.dumps({"dialogflow_input": dialogflow_input}))

    return blob_name


def send_gcs_dialogflow_output(session_id, timestamp, dialogflowcx_response):
    bucket_name = "id-conversation-data"
    blob_name = f"dialogflow_output/{session_id}-{timestamp}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(json.dumps(dialogflowcx_response))

    return blob_name


def send_gcs_slack_response(session_id, timestamp, slack_response):
    bucket_name = "id-conversation-data"
    blob_name = f"slack_response/{session_id}-{timestamp}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(json.dumps(slack_response))

    return blob_name


def update_gcs_session_table(session_id, timestamp, dialogflow_input_loc, dialogflow_output_loc, slack_response_loc):
    bucket_name = "id-conversation-data"
    blob_name = f"session_table/{session_id}-{timestamp}.json"
    storage_client = storage.Client(credentials=_get_credentials())
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    _dict = {
        "session_id": session_id,
        "create_ts": timestamp,
        "update_ts": timestamp,
        "active": 1,
        "this_loc": blob_name,
        "dialogflow_input_loc": dialogflow_input_loc,
        "dialogflow_output_loc": dialogflow_output_loc,
        "slack_response_loc": slack_response_loc
    }
    blob.upload_from_string(json.dumps(_dict))

    return blob_name


# [START functions_slack_search]
@functions_framework.http
def kg_search(request):
    print("*" * 20, "starting a new session", "*" * 20)
    #    try:
    global slack_message_text
    trigger_id = None
    view_id = None
    text_input = None
    data = None
    if request.method == 'POST':
        if request.is_json:
            print("seems like Text input")
            data = request.get_json()
            headers = request.headers
            print("data: ", data)
            if 'type' in data:
                if data['type'] == 'android_app_actions':
                    print("call from android app")
                    _input = data['actions'][0]
                    text_input = _input['text']['text']
                    if text_input == 'Show Goals':
                        print("trying to get goals list for android app")
                        response_data = {
                            "status": "successfully received your message of Show Goals on ID backend",
                            "message": "Show Goals call received from android app. Would be responding soon.",
                            "result": goals_comments_list()
                        }
                        print("response_data", response_data)
                        return make_response(jsonify(response_data), 200)
                    elif text_input == 'Show Tasks':
                        goal_id = data['goal_id']
                        print(f"trying to get tasks list for android app for goal id: {goal_id}")
                        response_data = {
                            "status": "successfully received your message of Show Tasks on ID backend",
                            "message": "Show Tasks call received from android app. Would be responding soon.",
                            "result": goal_tasks_comments_list(goal_id)
                        }
                        print("response_data", response_data)
                        return make_response(jsonify(response_data), 200)
                    elif text_input == 'Show Activities':
                        task_id = data['task_id']
                        print(f"trying to get activities list for android app for goal id: {task_id}")
                        response_data = {
                            "status": "successfully received your message of Show Activities on ID backend",
                            "message": "Show Activities call received from android app. Would be responding soon.",
                            "result": task_activities_comments_list(task_id)
                        }
                        print("response_data", response_data)
                        return make_response(jsonify(response_data), 200)
                    else:
                        print("Unidentified data received from android app")
                        response_data = {
                            "status": "successfully received your message on ID backend",
                            "message": "Unidentified data received from android app. Would be checking soon.",
                            "result": []
                        }
                        print("response_data", response_data)
                        return make_response(jsonify(response_data), 200)

            if 'challenge' in data:
                verify_signature(request)
                return jsonify({'challenge': data['challenge']})
            elif 'X-Slack-Retry-Num' in headers:
                print("seems like a retry: ", headers['X-Slack-Retry-Num'])
                return '', 200
            elif 'bot_id' in data['event'].keys():
                print("seems like a bot message, so ignoring")
                return '', 200
            if 'message' in data['event'].keys():
                if 'bot_id' in data['event']['message'].keys():
                    print("seems like a bot message, so ignoring")
                    return '', 200
            else:
                text_input = data['event']['blocks'][0]['elements'][0]['elements'][0]['text']
                if 'trigger_id' in data.keys():
                    print("trigger_id: ", trigger_id)
                    trigger_id = data['trigger_id']
        else:
            data = json.loads(request.form.get('payload'))
            print("data: ", data)
            if data['type'] == 'block_actions':
                print("seems like Actions input")
                _input = data['actions'][0]
                if 'selected_option' in _input.keys():
                    print("seems like Actions-option-select input")
                    text_input = _input['selected_option']['value']
                    if _input['action_id'] == 'frequency_select' and text_input in ['Once', 'Daily', 'Weekly',
                                                                                    'Monthly', 'Yearly']:
                        print("seems like a frequency selection input, so ignoring")
                        return '', 200
                    elif _input['action_id'] == 'auto_activity_creation_select' and text_input in ['Yes', 'No']:
                        print("seems like a auto_activity_creation_select selection input, so ignoring")
                        return '', 200
                elif 'Mark as finished' in _input['text']['text']:
                    print("seems like Mark as finished input")
                    text_input = _input['value']
                else:
                    print("seems like Actions-text input")
                    text_input = _input['text']['text']
            elif data['type'] == 'view_submission':
                print('seems like view_submission input')
                text_input = 'view_submission'
                if not ('private_metadata' in data['view'].keys()):
                    print("no private_metadata in view_submission. aborting")
                    return '', 200
            else:
                print('unrecognised input type:', data['type'])
                return '', 200
            if 'trigger_id' in data.keys():
                trigger_id = data['trigger_id']
                print("trigger_id: ", trigger_id)
            if 'view' in data.keys():
                view_id = data['view']['id']
                print("view_id: ", view_id)

    # text_input = request.form["text"]
    print("text_input: ", text_input)
    # print('slack_message_text: ', slack_message_text)
    # if text_input == slack_message_text:
    #     print("possible infinite loop! Halting!")
    #     return '', 200

    slack_message_text = text_input
    # payload_input = json.loads(request.form.get('payload'))
    # print("payload_input: ", payload_input)
    if text_input is not None:
        dialogflow_input = text_input
    else:
        dialogflow_input = ' '
    # elif payload_input is not None:
    #     dialogflow_input = payload_input['actions'][0]['value']

    service, session_id, match_intent_body = get_dialogflow_inputs(dialogflow_input)
    if text_input == 'Show Goals List':
        dialogflowcx_response = create_goals_list_modal()  # here dialogflowcx_response is modal_response
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
    elif 'view-goal-tasks' in text_input:
        dialogflowcx_response = create_view_goal_tasks_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'edit-goal' in text_input:
        dialogflowcx_response = create_goal_edit_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'archive-goal' in text_input:
        dialogflowcx_response = create_goal_archive_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'finish-goal' in text_input:
        dialogflowcx_response = create_goal_archive_modal(text_input, action_type='finish')
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'activate-goal' in text_input:
        dialogflowcx_response = create_goal_archive_modal(text_input, action_type='activate')
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'Add New Goal' in text_input:
        dialogflowcx_response = create_new_goal_modal()
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'view-task-activities' in text_input:
        dialogflowcx_response = create_view_task_activities_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'edit-task' in text_input:
        dialogflowcx_response = create_task_edit_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'archive-task' in text_input:
        dialogflowcx_response = create_task_archive_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'finish-task' in text_input:
        dialogflowcx_response = create_task_archive_modal(text_input, action_type='finish')
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'Add New Task' in text_input:
        goal_id = None
        if 'actions' in data.keys():
            for action in data['actions']:
                if 'create_new_task' in action['action_id']:
                    goal_id = action['action_id'].rsplit('create_new_task_goal-id:', 1)[-1]
        print("inferred goal_id: ", goal_id)
        if goal_id is None:
            print("goal_id not sent into Add new task modal. Quitting!")
            return '', 200
        dialogflowcx_response = create_new_task_modal(goal_id)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'edit-activity' in text_input:
        dialogflowcx_response = create_activity_edit_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'Add New Activity' in text_input:
        task_id = None
        if 'actions' in data.keys():
            for action in data['actions']:
                if 'create_new_activity' in action['action_id']:
                    task_id = action['action_id'].rsplit('create_new_activity_task-id:', 1)[-1]
        print("inferred task_id: ", task_id)
        if task_id is None:
            print("task_id not sent into Add new activity modal. Quitting!")
            return '', 200
        dialogflowcx_response = create_new_activity_modal(task_id)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'archive-activity' in text_input:
        dialogflowcx_response = create_activity_archive_modal(text_input)
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif 'finish-activity' in text_input:
        dialogflowcx_response = create_activity_archive_modal(text_input, action_type='finish')
        slack_response = get_slack_response(session_id, dialogflowcx_response, action_type='direct_modal')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id, view_id=view_id)
    elif data['type'] == 'view_submission':
        pairs = data['view']['private_metadata'].split(',')
        metadata = {}
        for pair in pairs:
            key, value = pair.split(':')
            metadata[key] = value
        if metadata['action'] == 'edit-goal':
            print('trying to edit goal with inputted information')
            goal_id = metadata['goal_id']
            dialogflowcx_response = submit_goal_edit_input(goal_id, data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'archive-goal':
            print('trying to archive goal with inputted information')
            goal_id = metadata['goal_id']
            dialogflowcx_response = submit_goal_status_update(goal_id)
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'finish-goal':
            print('trying to archive goal with inputted information')
            goal_id = metadata['goal_id']
            dialogflowcx_response = submit_goal_status_update(goal_id, action_type='finish')
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'activate-goal':
            print('trying to archive goal with inputted information')
            goal_id = metadata['goal_id']
            dialogflowcx_response = submit_goal_status_update(goal_id, action_type='activate')
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'create-goal':
            print('trying to create goal with inputted information')
            goal_id = create_session_id()
            dialogflowcx_response = submit_goal_create_input(goal_id, data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'edit-task':
            print('trying to edit task with inputted information')
            task_id = metadata['task_id']
            dialogflowcx_response = submit_task_edit_input(task_id, data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'archive-task':
            print('trying to archive task with inputted information')
            task_id = metadata['task_id']
            dialogflowcx_response = submit_task_status_update(task_id)
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'finish-task':
            print('trying to archive task with inputted information')
            task_id = metadata['task_id']
            dialogflowcx_response = submit_task_status_update(task_id, action_type='finish')
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'create-task':
            print('trying to create task with inputted information')
            task_id = create_session_id()
            dialogflowcx_response = submit_task_create_input(task_id, metadata['goal_id'],
                                                             data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'create-activity':
            print('trying to create activity with inputted information')
            activity_id = create_session_id()
            dialogflowcx_response = submit_activity_create_input(activity_id, metadata['task_id'],
                                                                 data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'archive-activity':
            print('trying to archive activity with inputted information')
            activity_id = metadata['activity_id']
            dialogflowcx_response = submit_activity_status_update(activity_id)
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'finish-activity':
            print('trying to finish activity with inputted information')
            activity_id = metadata['activity_id']
            dialogflowcx_response = submit_activity_status_update(activity_id, action_type='finish')
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        elif metadata['action'] == 'edit-activity':
            print('trying to edit activity with inputted information')
            activity_id = metadata['activity_id']
            dialogflowcx_response = submit_activity_edit_input(activity_id, data['view']['state']['values'])
            slack_response = get_slack_response(session_id, dialogflowcx_response,
                                                action_type='submission_notification')
            send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
        else:
            print('unrecognised action for view_submission: ', metadata['action'])
            return '', 200
    elif 'remind-again' in text_input:
        print("seems like suggestion reminder to be recreated")
        _temp = text_input.split('remind-again-', 1)[-1]
        if '-min-' in _temp:
            time_delay = int(_temp.split('-min-', 1)[0])
            activity_id = _temp.split('-min-', 1)[1]
        elif 'later-' in _temp:
            time_delay = 120        # currently setting to 2 hours later
            activity_id = _temp.split('later-', 1)[1]
        else:
            print(f'unrecognized input for remind-again: {_temp}')
            return '', 200
        dialogflowcx_response = submit_activity_edit_suggestion_time(activity_id, time_delay)
        slack_response = get_slack_response(session_id, dialogflowcx_response,
                                            action_type='submission_notification')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
    elif 'mark-as-finished-' in text_input:
        print("seems activity is to be marked as finished as per suggestion reminder input")
        activity_id = text_input.split('mark-as-finished-', 1)[-1]
        dialogflowcx_response = submit_activity_status_update(activity_id, action_type='finish')
        slack_response = get_slack_response(session_id, dialogflowcx_response,
                                            action_type='submission_notification')
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id)
    else:
        print("triggering dialogflow cx with match_intent_body: ", match_intent_body)
        dialogflowcx_response = get_fulfillment(service, session_id, match_intent_body)
        slack_response = get_slack_response(session_id, dialogflowcx_response)
        send_slack_response(slack_response=slack_response, trigger_id=trigger_id)

    print("slack_response sent:", slack_response)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d-%H:%M:%S")
    dialogflow_input_loc = send_gcs_dialogflow_input(session_id, timestamp, dialogflow_input)
    dialogflow_output_loc = send_gcs_dialogflow_output(session_id, timestamp, dialogflowcx_response)
    slack_response_loc = send_gcs_slack_response(session_id, timestamp, slack_response)
    session_table_loc = update_gcs_session_table(session_id, timestamp, dialogflow_input_loc,
                                                 dialogflow_output_loc, slack_response_loc)

    print("dialogflow_input_loc: ", dialogflow_input_loc)
    print("dialogflow_output_loc: ", dialogflow_output_loc)
    print("slack_response_loc: ", slack_response_loc)
    print("session_table_loc: ", session_table_loc)

    # if payload['type'] == 'block_actions':
    #    original_message = payload['actions'][0]['value']
    #     client.chat_postMessage(channel=payload['channel']['id'], text=original_message)
    #     client.chat_postMessage(channel=payload['channel']['id'],
    #     text=slack_args['text'], blocks=slack_args['blocks'])

    # url = os.environ['SLACK_WEBHOOK_URL']
    # webhook = WebhookClient(url)
    # webhook.send(text=f"<@id_development> {original_message}")

    # Send acknowledgment response
    return '', 200


#    except Exception as e:
#        print("Exception: ", e)
#        return '', 200


if __name__ == '__main__':
    # app.run()
    pass

# [END functions_slack_search]
