import os
import logging
import json
import time
import threading
import requests
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve Slack credentials from environment variables
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SALESFORCE_API_URL = os.getenv("SALESFORCE_API_URL")
SALESFORCE_ACCESS_TOKEN = os.getenv("SALESFORCE_ACCESS_TOKEN")

# Initialize Slack App (No Flask)
slack_app = App(token=SLACK_BOT_TOKEN)

# Dynamic Action Handling for Approve & Reject
@slack_app.action(re.compile(r"^(approve|reject)_action_(\w+)$"))
def handle_approval_action(ack, body, say, logger, context, action):
    ack()  # Acknowledge the action
    logger.info("handle_approval_action")

    user_id = body["user"]["id"]
    action_id = action["action_id"]  # Example: "approve_action_500ep0000024aVHAAY"
    action_type, record_id = action_id.split("_action_")  # Splitting at "_action_"
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    
    # Fetch user info safely
    user_info = slack_app.client.users_info(user=user_id)
    user_profile = user_info.get("user", {}).get("profile", {})

    # Use email if available, otherwise use Slack ID
    user_email = user_profile.get("email", f"SlackUser-{user_id}")

    # Determine action type
    decision = "Approved ✅" if action_type == "approve" else "Rejected ❌"

    logger.info(f"User {user_email} selected {decision} for Case {record_id}")

    # Retrieve the original message's blocks
    original_blocks = body["message"]["blocks"]

    # Remove the buttons by filtering out the "actions" block
    updated_blocks = [
        block for block in original_blocks if block.get("type") != "actions"
    ]

    # Append a new section block with the decision text
    updated_blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*This case has been {decision}*"
            }
        }
    )

    # Update the Slack message to reflect the decision
    slack_app.client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"*Approval Needed: High Priority Case*",  # Preserve the title text
        blocks=updated_blocks
    )

    # Send the approval decision to Salesforce
    send_approval_decision_to_salesforce(record_id, action_type, user_email)

    # Post a follow-up message in the thread with user decision
    slack_app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=message_ts,
        text=f"_<@{user_id}> ({user_email}) has {decision} this Case._"
    )

def send_approval_decision_to_salesforce(record_id, decision, user_email):
    logger.info("send_approval_decision_to_salesforce")

    # Ensure the correct case format for Salesforce
    decision_mapping = {
        "approve": "Approved",
        "reject": "Rejected"
    }
    
    salesforce_decision = decision_mapping.get(decision.lower(), decision)  # Ensure proper mapping

    salesforce_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
    logger.info(f"Using Salesforce Access Token: {salesforce_token}")

    payload = {
        "recordId": record_id.strip(),
        "decision": salesforce_decision,  # Mapped decision
        "userEmail": user_email.strip()
    }

    headers = {
        "Authorization": f"Bearer {salesforce_token}",
        "Content-Type": "application/json"
    }

    logger.info(f"***Payload Sent to Salesforce:\n{json.dumps(payload, indent=2)}***")

    response = requests.post(SALESFORCE_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        logger.info(f"Successfully updated approval in Salesforce for record {record_id}")
    else:
        logger.error(f"Failed to update approval in Salesforce: {response.text}")

@slack_app.event("app_home_opened")
def handle_app_home_opened(event):
    """Handles the app_home_opened event and updates the Slack Home tab."""
    try:
        with open("block-kit/app_home_default.json","r") as file:
            app_home_json = json.load(file)
    except Exception as e:
        logger.error(f"Error loading app_home.json to app_home_json: {e}")

    try:
        slack_app.client.views_publish(
            user_id=event["user"],
            view=app_home_json
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

### RUN SLACK IN A SEPARATE THREAD ###
def run_slack():
    """Runs the Slack Bolt app using Socket Mode."""
    logger.info("Starting Slack App...")
    try:
        handler = SocketModeHandler(slack_app, SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        logger.error(f"Failed to start Socket Mode: {e}")
        os._exit(1)  # Force shutdown to prevent lingering processes

if __name__ == "__main__":
    # Start Slack App in Socket Mode
    run_slack()