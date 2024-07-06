true = "true"
list_goals_modal_template = {
    "type": "modal",
    "submit": {
        "type": "plain_text",
        "text": "Ok",
        "emoji": true
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": true
    },
    "title": {
        "type": "plain_text",
        "text": "List of Goals",
        "emoji": true
    },
    "blocks": []
}


def create_single_goal_block(goal_id):
    goal_name = ""  # get goal name based on goal_id
    goal_description = ""  # get goal_description based on goal_id
    goal_details = ""  # get goal_details based on goal_id
    next_task = ""  # get next_task based on goal_id
    next_step = ""  # get next_step based on goal_id
    scheduled_time = ""  # get scheduled_time based on goal_id

    return {'block': [
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{goal_name}*\n {goal_description}\n {goal_details}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Next Task/Step: {next_task}/{next_step}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"scheduled at: {scheduled_time}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details",
                        "emoji": true
                    },
                    "value": f"show_details_{goal_id}"
                }
            ]
        }
    ]}
