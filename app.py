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

# Refresh SALESFORCE_ACCESS_TOKEN
def get_salesforce_access_token():
    """Fetch a new Salesforce access token."""
    auth_url = "https://oasis-acf--analysis.sandbox.my.salesforce.com/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": os.getenv("SALESFORCE_CLIENT_ID"),
        "client_secret": os.getenv("SALESFORCE_CLIENT_SECRET"),
        "username": os.getenv("SALESFORCE_USERNAME"),
        "password": os.getenv("SALESFORCE_PASSWORD")
    }
    response = requests.post(auth_url, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        logger.error(f"Failed to get Salesforce access token: {response.text}")
        return None

# Dynamic Action Handling for Approve & Reject
@slack_app.action(re.compile(r"^(approve|reject)_action_(\w+)$"))
def handle_approval_action(ack, body, say, logger, context, action):
    ack()  # Acknowledge the action
    logger.info("handle_approval_action")

    user_id = body["user"]["id"]
    action_id = action["action_id"]  # Example: "approve_action_500ep0000024aVHAAY"
    action_type, record_id = action_id.split("_action_")  # Splitting at "_action_"

    # Fetch user info safely
    user_info = slack_app.client.users_info(user=user_id)
    user_profile = user_info.get("user", {}).get("profile", {})

    # Use email if available, otherwise use Slack ID
    user_email = user_profile.get("email", f"SlackUser-{user_id}")

    # Determine action type
    decision = "Approved ✅" if action_type == "approve" else "Rejected ❌"

    logger.info(f"User {user_email} selected {decision} for Case {record_id}")

    # Update the Slack message to reflect the decision
    slack_app.client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"*Case {record_id} has been {decision}*",
        blocks=[]
    )

    # Send the approval decision to Salesforce
    send_approval_decision_to_salesforce(record_id, action_type, user_email)

    say(f"User <@{user_id}> ({user_email}) has {decision} Case {record_id}.")

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

        
def build_home_view():
    """Constructs and returns the Block Kit layout for the Slack App Home tab."""
    return {
        "type": "home",
        "blocks": [
            {
                "type": "actions",
                "block_id": "filter_options",
                "elements": [
                    {
                        "type": "static_select",
                        "placeholder": {"type": "plain_text", "text": "Status", "emoji": True},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Pending", "emoji": True}, "value": "pending"},
                            {"text": {"type": "plain_text", "text": "Approved", "emoji": True}, "value": "approved"},
                            {"text": {"type": "plain_text", "text": "Rejected", "emoji": True}, "value": "rejected"},
                            {"text": {"type": "plain_text", "text": "Recalled", "emoji": True}, "value": "recalled"}
                        ],
                        "action_id": "status_select"
                    },
                    {
                        "type": "static_select",
                        "placeholder": {"type": "plain_text", "text": "Assigned to", "emoji": True},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Assigned to me", "emoji": True}, "value": "assigned_to_me"},
                            {"text": {"type": "plain_text", "text": "All", "emoji": True}, "value": "all"}
                        ],
                        "action_id": "assignee_select"
                    }
                ]
            },
            {"type": "divider"}
        ]
    }

@slack_app.event("app_home_opened")
def handle_app_home_opened(event):
    """Handles the app_home_opened event and updates the Slack Home tab."""
    user_id = event.get("user")
    if not user_id:
        logger.error("Missing user ID in event payload")
        return
    
    logger.info(f"Updating App Home for user: {user_id}")

    slack_app.client.views_publish(
        user_id=user_id,
        view=build_home_view()
    )

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