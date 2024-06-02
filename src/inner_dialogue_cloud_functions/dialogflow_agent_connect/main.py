import functions_framework
import json
import os
import requests
from google.oauth2 import service_account
from googleapiclient import discovery
from requests import Response
import uuid


@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    return 'Hello {}!'.format(name)


def _get_credentials():
    credentials = os.environ.get("CREDENTIALS")
    svc = json.loads(credentials.replace("\'", "\""))
    return service_account.Credentials.from_service_account_info(svc)


def _upload_source_code_using_upload_url(upload_url: str, data):
    # Prepare Header and data for PUT request
    # https://cloud.google.com/functions/docs/reference/rest/v1/projects.locations.functions/generateUploadUrl
    headers = {
        "content-type": "application/zip"
    }
    response: Response = requests.put(upload_url, headers=headers, data=data)
    print(f"HTTP Status Code for uploading data: {response.status_code} \n")
    print(f"Response body: {response.json} \n")


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


def _run(request):
    text_input = request.form["text"] if 'text' in request.form.get else None
    payload_input = json.loads(request.form.get('payload')) if 'payload' in request.form.get else None
    if text_input is not None:
        dialogflow_input = text_input
    elif payload_input is not None:
        dialogflow_input = payload_input['actions'][0]['value']
    else:
        dialogflow_input = ' '

    gcp_project = "useful-proposal-424218-t8"  # os.environ.get("GCP_PROJECT")
    gcp_region = "global"  # os.environ.get("GCP_REGION")
    agent_id = "bf349865-2a23-44ba-84bb-680fd5047e20"

    loc_parent = f"projects/{gcp_project}/locations/{gcp_region}"

    service = discovery.build(
        "dialogflow", "v3"
        # , credentials=_get_credentials()
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

    dialogflowcx_response = get_fulfillment(service, session_id, match_intent_body)
    slack_args = {'text': '', 'blocks': []}
    for response_message in dialogflowcx_response['queryResult']['responseMessages']:
        if 'text' in response_message.keys():
            slack_args['text'] = response_message['text']['text'][0]  # need to check [1] and more?
        elif 'payload' in response_message.keys():
            slack_args['blocks'] = response_message['payload']['blocks']
        else:
            pass
    # print('Text Result:', dialogflowcx_response['queryResult']['responseMessages'][0]['text']['text'][0])
    # print('Additional Payload:', dialogflowcx_response['queryResult']['responseMessages'][1]['payload'])


def create_session_id():
    return uuid.uuid4()


if __name__ == '__main__':
    _run()

# Adding this for testing the GitHub Action code 8 May 2024 evening when its heavily raining
