import os, base64
import functions_framework
from todoist_api_python.api import TodoistAPI


# Triggered from a message on a Cloud Pub/Sub topic, every night at 12AM
@functions_framework.cloud_event
def hello_pubsub(cloud_event):
    # Print out the data from Pub/Sub, to prove that it worked
    print(base64.b64decode(cloud_event.data["message"]["data"]))
    api = TodoistAPI(os.environ['TODOIST_API_TOKEN'])

    try:
        projects = api.get_projects()
        print(projects)
    except Exception as error:
        print(error)
