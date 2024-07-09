from googleapiclient import discovery
from auth_utils import _get_credentials
import base64


def encode_to_base64(input_string):
    byte_string = input_string.encode('utf-8')
    base64_bytes = base64.b64encode(byte_string)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string


def create_scheduler_job(data_str, schedule):
    gcp_project = 'useful-proposal-424218-t8'
    gcp_region = 'asia-south1'
    _parent = f"projects/{gcp_project}/locations/{gcp_region}"

    scheduler_body = {
        "pubsubTarget": {
            "data": encode_to_base64(data_str),
            "topicName": f"projects/{gcp_project}/topics/id-activity-suggestion"
        },
        "schedule": f"{schedule}"
    }
    service = discovery.build(
        "cloudscheduler", "v1", credentials=_get_credentials()
    )
    print('attempting to create the scheduler job with scheduler_body: ', scheduler_body)
    # noqa https://googleapis.github.io/google-api-python-client/docs/dyn/cloudscheduler_v1.projects.locations.jobs.html#create
    scheduler_jobs_obj = service.projects().locations().jobs()
    scheduler_job = scheduler_jobs_obj.create(parent=_parent, body=scheduler_body).execute()

    print("scheduler_job created: ", scheduler_job, " with data:", data_str)
    return scheduler_job


def update_scheduler_job(scheduler_name, data_str, schedule):
    print('attempting to delete old scheduler:', scheduler_name, ' and create a new one')
    service = discovery.build(
        "cloudscheduler", "v1", credentials=_get_credentials()
    )
    # noqa https://googleapis.github.io/google-api-python-client/docs/dyn/cloudscheduler_v1.projects.locations.jobs.html#create
    scheduler_jobs_obj = service.projects().locations().jobs()
    scheduler_del_job = scheduler_jobs_obj.delete(name=scheduler_name).execute()
    print("scheduler job deleted:", scheduler_name, " output:", scheduler_del_job)

    new_scheduler = create_scheduler_job(data_str, schedule)
    print("scheduler_job created: ", new_scheduler, " with data:", data_str)
    return new_scheduler
