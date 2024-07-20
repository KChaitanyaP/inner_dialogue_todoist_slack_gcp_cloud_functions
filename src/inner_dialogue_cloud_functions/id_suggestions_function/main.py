import base64
import uuid
from cloudevents.http import CloudEvent
import functions_framework
from slack.signature import SignatureVerifier
from slack_sdk import WebClient
from auth_utils import _get_credentials
from google.cloud import bigquery
import os
from suggestion_messages import *
from suggestion_blocks import *

tz = 'Asia/Kolkata'  # current user timezone is Asia/Kolkata, need to make it dynamic


def create_session_id():
    return uuid.uuid4()


def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ["SLACK_SECRET"])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError("Invalid request/credentials.")


def get_session_id_block(session_id):
    return [{
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"session id:`{str(session_id)}`"
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


@functions_framework.cloud_event
def entrypoint(cloud_event: CloudEvent) -> None:
    print("*" * 20, "starting a new session", "*" * 20)
    activity_id = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    client = bigquery.Client(credentials=_get_credentials())

    query = f"""SELECT steps_table.*, 
tasks_table.task_name, tasks_table.comments as task_comments, goals_table.goal_name 
FROM `useful-proposal-424218-t8.inner_dialogue_data.steps` as steps_table 
join `useful-proposal-424218-t8.inner_dialogue_data.tasks` as tasks_table on steps_table.task_id=tasks_table.task_id
join `useful-proposal-424218-t8.inner_dialogue_data.goals` as goals_table on tasks_table.goal_id=goals_table.goal_id
where step_id='{activity_id}';
    """
    print("query: ", query)
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    rows = [dict(row) for row in result]
    activity_details = rows[0]
    print("activity_details along with task name and goal name: ", activity_details)

    activity_suggestion_template = get_basic_suggestion_template(activity_id)
    for block in activity_suggestion_template['blocks']:
        if 'block_id' in block.keys():
            if block['block_id'] == 'message-block':
                block['text']['text'] = activity_suggestion_msg_v1(activity_details)

    print('trying to send suggestion message')
    slack_response = get_slack_response(create_session_id(), activity_suggestion_template,
                                        action_type='submission_notification')
    send_slack_response(slack_response=slack_response)

