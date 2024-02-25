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
   3. Google App Engine: This is great option too.
   4. Maybe more options: Need to check the options as we go along.

3. For the quickest possible prototyping, I am planning to go ahead with Google Cloud Functions.
    
-[ ] Create the automated script (using terraform?) to set up billing alerts and the whole process.
   - Probably all script automation (for cloud build) could be inspired from jumpstart solutions like 
  [this one](https://console.cloud.google.com/products/solutions/details/dynamic-web-app?hl=en&project=fifth-glazing-415313)
  

### Resources

[^1]: https://www.googlecloudcommunity.com/gc/Cloud-Hub/Cannot-make-a-folder-in-google-cloud-free-tier/m-p/613412#M2699