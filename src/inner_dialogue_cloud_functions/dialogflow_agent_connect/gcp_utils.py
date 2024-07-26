from google.cloud import storage
import json
import os


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


if __name__ == '__main__':
    _bucket_name = "inner-dialogue-conv-data"
    _folder_prefix = "steps-data"
    read_update_save_gcs(_bucket_name, _folder_prefix)
