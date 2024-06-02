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
import os, json

from flask import jsonify
import functions_framework
from googleapiclient import discovery
from google.oauth2 import service_account
from slack.signature import SignatureVerifier
from slack_sdk import WebClient
from slack_sdk.webhook import WebhookClient
from requests import Response
import uuid


# [START functions_verify_webhook]
def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ["SLACK_SECRET"])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError("Invalid request/credentials.")


# [END functions_verify_webhook]
def _get_credentials():
    credentials = os.environ.get("CREDENTIALS")
    svc = json.loads(credentials.replace("\'", "\""))
    return service_account.Credentials.from_service_account_info(svc)


# [START functions_slack_format]
def format_slack_message(query, response):
    entity = None
    if (
            response
            and response.get("itemListElement") is not None
            and len(response["itemListElement"]) > 0
    ):
        entity = response["itemListElement"][0]["result"]

    message = {
        "response_type": "in_channel",
        "text": f"Query: {query}",
        "attachments": [],
    }

    attachment = {}
    if entity:
        name = entity.get("name", "")
        description = entity.get("description", "")
        detailed_desc = entity.get("detailedDescription", {})
        url = detailed_desc.get("url")
        article = detailed_desc.get("articleBody")
        image_url = entity.get("image", {}).get("contentUrl")

        attachment["color"] = "#3367d6"
        if name and description:
            attachment["title"] = "{}: {}".format(entity["name"], entity["description"])
        elif name:
            attachment["title"] = name
        if url:
            attachment["title_link"] = url
        if article:
            attachment["text"] = article
        if image_url:
            attachment["image_url"] = image_url
    else:
        attachment["text"] = "No results match your query."
    message["attachments"].append(attachment)

    return message


# [START functions_slack_request]
def make_search_request(query):
    res = query
    return format_slack_message(query, res)


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


# [START functions_slack_search]
@functions_framework.http
def kg_search(request):
    print("request form: ", request.form)
    if request.method == 'POST':
        data = request.get_json()
        print("data: ", data)
        # Responds to Slack's verification challenge
        if 'challenge' in data:
            verify_signature(request)
            return jsonify({'challenge': data['challenge']})
        else:
            pass

    # text_input = request.form["text"]
    text_input = data['event']['blocks'][0]['elements'][0]['elements'][0]['text']
    print("text_input: ", text_input)
    # payload_input = json.loads(request.form.get('payload'))
    # print("payload_input: ", payload_input)
    if text_input is not None:
        dialogflow_input = text_input
    else:
        dialogflow_input = ' '
    # elif payload_input is not None:
    #     dialogflow_input = payload_input['actions'][0]['value']

    gcp_project = "useful-proposal-424218-t8"  # os.environ.get("GCP_PROJECT")
    gcp_region = "global"  # os.environ.get("GCP_REGION")
    agent_id = "bf349865-2a23-44ba-84bb-680fd5047e20"

    loc_parent = f"projects/{gcp_project}/locations/{gcp_region}"

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

    dialogflowcx_response = get_fulfillment(service, session_id, match_intent_body)
    slack_args = {'text': '', 'blocks': []}
    for response_message in dialogflowcx_response['queryResult']['responseMessages']:
        if 'text' in response_message.keys():
            slack_args['text'] = response_message['text']['text'][0]  # need to check [1] and more?
        elif 'payload' in response_message.keys():
            slack_args['blocks'] = response_message['payload']['blocks']
        else:
            pass

    client = WebClient(token=os.environ['SLACK_OAUTH_TOKEN'])
    # print("request: ", request)
    # kg_search_response = make_search_request(request.form["text"])
    # return jsonify(kg_search_response)
    channel_id = 'D075T6SAUBD'
    client.chat_postMessage(channel=channel_id, text=slack_args['text'], blocks=slack_args['blocks'])
    # if payload['type'] == 'block_actions':
    #    original_message = payload['actions'][0]['value']
    #     client.chat_postMessage(channel=payload['channel']['id'], text=original_message)
    #     client.chat_postMessage(channel=payload['channel']['id'], text=slack_args['text'], blocks=slack_args['blocks'])

    # url = os.environ['SLACK_WEBHOOK_URL']
    # webhook = WebhookClient(url)
    # webhook.send(text=f"<@id_development> {original_message}")

    # Send acknowledgment response
    return '', 200


if __name__ == '__main__':
    app.run()

# [END functions_slack_search]
