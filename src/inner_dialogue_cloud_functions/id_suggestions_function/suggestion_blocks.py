true = True


def get_basic_suggestion_template(activity_id):
    suggestion_block = {
        "blocks": [
            {
                "type": "section",
                "block_id": "message-block",
                "text": {
                    "type": "mrkdwn",
                    "text": "<Add your text here>."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "block_id": "reminder-block",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Remind me in*"
                },
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "emoji": true,
                        "text": "Choose a time"
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "emoji": true,
                                "text": "15 min"
                            },
                            "value": f"remind-again-15-min-{activity_id}"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "emoji": true,
                                "text": "30 min"
                            },
                            "value": f"remind-again-30-min-{activity_id}"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "emoji": true,
                                "text": "45 min"
                            },
                            "value": f"remind-again-45-min-{activity_id}"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "emoji": true,
                                "text": "Later"
                            },
                            "value": f"remind-again-later-{activity_id}"
                        }
                    ]
                }
            },
            {
                "type": "section",
                "block_id": "finished-block",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Sure! Let’s do it right away.*"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Mark as finished",
                        "emoji": true
                    },
                    "style": "primary",
                    "value": f"mark-as-finished-{activity_id}",
                    "action_id": "button-action"
                }
            }
        ]
    }
    return suggestion_block
