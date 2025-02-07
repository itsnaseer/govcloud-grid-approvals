# 🚀 Salesforce-Slack Approval Integration

## Overview
This proof of concept integrates **Slack** and **Salesforce Gov Cloud** to enable approval workflows directly from Slack. Users can approve or reject Salesforce Cases within Slack, and the status updates are reflected in Salesforce. The implementation **bypasses Salesforce's built-in approval process** and directly updates case records.

DO NOT DEPLOY THIS TO PRODUCTION. This app uses some shortcuts like environment variables for simplicity. Not great for real world use. 

---

## 🔄 Process Flow
1. **Case Creation in Salesforce**
   - A **new case** is created in Salesforce with a **High** priority.

2. **Slack Notification**
   - A Slack message is sent with **Approve ✅ / Reject ❌** action buttons.

3. **User Decision (Slack App)**
   - Clicking **Approve** or **Reject** triggers a **Slack Action Handler**.

4. **ApprovalResponse (Apex Class in Salesforce)**
   - Based on the Slack decision:
     - **If Approved** → Update **Status = In Progress**
     - **If Rejected** → Update **Status = New** and **Priority = Medium**

5. **Salesforce Case Updates Automatically**
   - The Salesforce record reflects the updated status and priority.

---

## 🏗️ Components & Implementation

### **1️⃣ Slack App (Python + Bolt Framework)**
- Handles **user actions** from Slack (approve/reject clicks)
- Extracts **Case ID & User Details**
- Sends an API request to Salesforce via the `ApprovalResponse` endpoint

#### **Key Code Snippets (Python)**
```python
@slack_app.action(re.compile(r"^(approve|reject)_action_(\w+)$"))
def handle_approval_action(ack, body, say, logger, context, action):
    ack()  # Acknowledge the action
    user_id = body["user"]["id"]
    action_id = action["action_id"]  # Example: "approve_action_500ep0000024aVHAAY"
    action_type, record_id = action_id.split("_action_")
    decision = "Approved" if action_type == "approve" else "Rejected"
    
    # Send approval decision to Salesforce
    send_approval_decision_to_salesforce(record_id, decision, user_email)
```

---

### **2️⃣ ApprovalResponse (Apex Class in Salesforce)**
- Exposes a **REST API Endpoint (`/services/apexrest/ApprovalResponse`)**
- Receives **recordId, decision, and userEmail** from Slack
- **Directly updates the Case record** (bypasses standard approval process)

#### **Key Code Snippets (Apex)**
Check out the `.apex` snippets in the code repsitory. 
- SlackApprovalNotifier sets up the Flow Action.
- ApprovalResponse is the end point for Slack to send the approval payload

---

## ⚙️ Environment Setup
### **🔹 Salesforce Setup**
1. **Enable Apex REST API Access**
2. **Deploy the `ApprovalResponse` Apex class**
3. **Deploy the `SlackApprovalNotifier` Apex class**
4. **Generate Salesforce OAuth Credentials** (Client ID & Secret)
5. **Create Slack App OAuth Token & Permissions**

## Environment Variables
Make sure to Set these values. 
```
SLACK_APP_TOKEN=
SLACK_BOT_TOKEN=
SALESFORCE_API_URL=YOUR_ORG_URL/services/apexrest/ApprovalResponse
SALESFORCE_ACCESS_TOKEN=
```

### **🔹 Slack App Setup**
1. **Install Python & Virtual Environment**
2. **Install dependencies (`slack_bolt`, `requests`, etc.)**
3. **Configure `.env` file with API credentials**
4. **Run the Flask-based Slack App**

---

## 🎯 Expected Behavior
✅ **User clicks Approve in Slack → Case moves to "In Progress" in Salesforce**
✅ **User clicks Reject in Slack → Case moves to "New", priority changes to "Medium"**
✅ **No Salesforce Approval Process is used; all updates are direct**

---

## 🔍 Testing & Debugging
- **Slack Logs** → Monitor `handle_approval_action()` for button click events.
- **Salesforce Logs** → Check `Apex Debug Logs` for API processing issues.
- **Curl Test for API** →
```sh
curl -X POST https://your-salesforce-instance/services/apexrest/ApprovalResponse \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"recordId": "YOUR_RECORD_ID", "decision": "Approved", "userEmail": "user@example.com"}'
```

---

