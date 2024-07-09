# inner_dialogue_todoist_slack_gcp_cloud_functions
inner_dialogue with front ends as todoist and slack apps with gcp_cloud_functions as backend.

## Process followed once GCP account is setup

1. Setup billing and alerts. This is a recommended step before creating any resources.
   1. This step may be used to enforce creating different projects for different ideas as 
   we can create billing budgets and alerts at  a project level.
   2. The whole procedure could be followed as per https://cloud.google.com/billing/docs/how-to/budgets
   3. Currently, I am creating projects under 'No Organisation' folder, 
   however I could set up an organisation (with a domain name) using Cloud Identity as described 
   [here](https://cloud.google.com/resource-manager/docs/creating-managing-organization) 
   4. Currently, I am using the project under Organisation directly without folders. 
   If I can create a folder and setup billing alerts at folder level, that would help with checking multiple
   projects at once. But I am not able to provide 'resourcemanager.folders.create' permission to 
   the main email ID principal[^1]. I even tried creating a service account but no use.
   - [ ] Create a folder to incorporate billing alerts at a higher level.
   - [ ] I enabled the Slack channel connection and installed the Mobile App. 
   Add Slack channel and mobile app to the billing alerts. 

2. Now let's get into creating resources for our ID workflow. 
Inner Dialogue in a basic version could be a REST API listening to 
some user requests (planning to use Slack as front end app for user in the prototyping phase)
and running a few modules to respond. There are a variety of ways to achieve this in Google Cloud.
   1. Google Cloud Functions: This could be a quick way to get started. However, 
   user profile creation and authentication wouldn't be available from the start in this case.
   2. Google Cloud Run: This is also a preferred way as we might have a lot of idle time without any user requests.
   [^Cloud_Run_Resource_1]
   3. Google App Engine: This is great option too.
   4. Maybe more options: Need to check the options as we go along.

3. For the quickest possible prototyping, I am planning to go ahead with Google Cloud Functions.
    
- [ ] Create the automated script (using terraform?) to set up billing alerts and the whole process.
   - Probably all script automation (for cloud build) could be inspired from jumpstart solutions like 
  [this one](https://console.cloud.google.com/products/solutions/details/dynamic-web-app?hl=en&project=fifth-glazing-415313)
  
4. I followed the tutorial as outlined [^Cloud_Run_Resource_2] as a great starting point.
and could successfully publish a Slack App that triggers a Cloud Function in the backend.

5. However, we have some issues to take care of:
   1. Authentication: As mentioned in the tutorial, this Cloud Function can be triggered by any users and is open to 
   internet. So one obvious thing to fix is authenticate only the Slack app to use the function.

### Created a testing setup for the cloud function
It is actually easy. We can just run main_test.py and it responds with slack compliant output.

## Creating the Todoist retrieval mechanism
I followed the following instructions (as mentioned in https://cloud.google.com/scheduler/docs/tut-gcf-pub-sub)
```commandline
gcloud services enable cloudscheduler.googleapis.com pubsub.googleapis.com
gcloud pubsub topics create cron-topic
gcloud pubsub subscriptions create cron-sub --topic cron-topic
```
Created a Cloud Scheduler Job to trigger a Cloud Pub Sub topic at every 12 AM.
The Cloud Pub Sub Topic has a subscribe option
Our Cloud Function is subscribed to this Pub/Sub topic and gets triggered automatically at 12 AM.

-[ ] need to work on automated cloud build from Github repo. 

### General Resources

[^1]: https://www.googlecloudcommunity.com/gc/Cloud-Hub/Cannot-make-a-folder-in-google-cloud-free-tier/m-p/613412#M2699
[^Cloud_Run_Resource_1]: https://cloud.google.com/python/django/run
[^Cloud_Run_Resource_2]: (https://cloud.google.com/functions/docs/tutorials/slack#querying_the_knowledge_graph_api)
- https://cloud.google.com/functions/docs/tutorials/slack#functions-deploy-command-python
- https://cloud.google.com/functions/docs/securing/authenticating
- https://cloud.google.com/scheduler/docs/tut-gcf-pub-sub

## DialogFlowCX Agent Connect Cloud Function:
- https://stackoverflow.com/questions/76861768/handle-button-click-events-in-interactive-messages-using-slack-api-with-python-f
- https://medium.com/google-cloud/cloud-functions-best-practices-2-4-optimize-the-cloud-functions-5874f9d8c8b5
- https://github.com/googleapis/python-storage/blob/main/samples/snippets/storage_fileio_write_read.py