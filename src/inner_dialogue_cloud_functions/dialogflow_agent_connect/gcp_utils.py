import copy

from google.cloud import storage
from activity_based_submissions import prepare_activity_scheduler
from google.cloud import bigquery
import json
from googleapiclient import discovery
import os
import base64


def encode_to_base64(input_string):
    byte_string = input_string.encode('utf-8')
    base64_bytes = base64.b64encode(byte_string)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string


def read_update_save_gcs(bucket_name, folder_prefix):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=folder_prefix)
    for blob in blobs:
        if not blob.name.endswith('/'):
            file_contents = blob.download_as_text()
            print(f'{blob.name}:')
            file_content_dict = json.loads(file_contents)
            # this is the update code, change as needed
            file_content_dict["metadata_dict"] = ""

            # file upload code
            blob_name = f"{folder_prefix}/{os.path.basename(blob.name)}"
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            with blob.open("w") as f:
                f.write(json.dumps(file_content_dict))
            print('goal data file to GCS')


def download_bucket(bucket_name, local_dir):
    # Initialize a client
    client = storage.Client()

    # Get the bucket
    bucket = client.get_bucket(bucket_name)

    # List all blobs in the bucket
    blobs = bucket.list_blobs()

    for blob in blobs:
        # Skip directories (blobs ending with '/')
        if blob.name.endswith('/'):
            continue

        # Create local path to save the file
        local_path = os.path.join(local_dir, blob.name)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Download the file
        blob.download_to_filename(local_path)
        print(f'Downloaded {blob.name} to {local_path}')


def upload_to_bucket(bucket_name, source_folder):
    # Initialize a client
    client = storage.Client()

    # Get the bucket
    bucket = client.get_bucket(bucket_name)

    # Walk through the directory structure
    for root, dirs, files in os.walk(source_folder):
        for file_name in files:
            # Full path to the local file
            local_file_path = os.path.join(root, file_name)

            # Relative path to construct the GCS object name
            relative_path = os.path.relpath(local_file_path, source_folder)
            blob_name = relative_path.replace("\\", "/")  # Use '/' for GCS paths

            # Create a new blob and upload the file's content
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_file_path)
            print(f'Uploaded {local_file_path} to gs://{bucket_name}/{blob_name}')


def create_scheduler_job(data_str, schedule):
    gcp_project = 'scenic-style-432903-u9'
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
        "cloudscheduler", "v1"
    )
    print('attempting to create the scheduler job with scheduler_body: ', scheduler_body)
    # noqa https://googleapis.github.io/google-api-python-client/docs/dyn/cloudscheduler_v1.projects.locations.jobs.html#create
    scheduler_jobs_obj = service.projects().locations().jobs()
    scheduler_job = scheduler_jobs_obj.create(parent=_parent, body=scheduler_body).execute()

    print("scheduler_job created: ", scheduler_job, " with data:", data_str)
    return scheduler_job


def create_scheduler_jobs():

    query = f"""SELECT * FROM `scenic-style-432903-u9.inner_dialogue_data.steps`"""
    print("query: ", query)
    client = bigquery.Client(project='scenic-style-432903-u9')
    query_job = client.query(query)
    result = query_job.result()  # Waits for query to finish
    job_list = [dict(row) for row in result]
    print("total scheduler jobs to be created: ", len(job_list))
    for i, activity_details in enumerate(job_list):
        scheduler_data, cron = prepare_activity_scheduler(activity_details)
        scheduler_job = create_scheduler_job(scheduler_data, cron)
        print(f"created {i} out of {len(job_list)} schedulers")

        bucket_name = "id-conversation-data"
        blob_name = f"steps-data/step-{activity_details['step_id']}.json"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        activity_details_updated = copy.deepcopy(activity_details)
        activity_details_updated['suggestion_notification_scheduler'] = scheduler_job['name']
        with blob.open("w") as f:
            f.write(json.dumps(activity_details_updated))
        print('saved edited activity file to GCS')


if __name__ == '__main__':
    """
    _bucket_name = "id-conversation-data"
    _folder_prefix = "steps-data"
    read_update_save_gcs(_bucket_name, _folder_prefix)
    
    # Usage example for downloading full bucket
    bucket_name = 'inner-dialogue-conv-data'
    local_directory = '/Users/chaitanyakeerthi/Downloads/temp/full_backup_18Aug'

    download_bucket(bucket_name, local_directory)
    
    # Usage example for uploading full bucket
    bucket_name = 'id-conversation-data'  # Replace with your bucket name
    local_directory = '/Users/chaitanyakeerthi/Downloads/temp/full_backup_18Aug'  # Replace with your local directory to upload

    upload_to_bucket(bucket_name, local_directory)
    """
    create_scheduler_jobs()
