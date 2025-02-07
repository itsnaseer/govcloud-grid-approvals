public with sharing class SlackApprovalNotifier {
    
    @InvocableMethod(label='Send Slack Case Approval' description='Sends a high-priority case approval request to Slack')
    public static void sendCaseApproval(List<ApprovalRequest> requests) {
        for (ApprovalRequest request : requests) {
            sendSlackMessage(request);
        }
    }

    private static void sendSlackMessage(ApprovalRequest request) {
        String slackApiUrl = 'https://slack.com/api/chat.postMessage';

        // 🔹 Ensure `details` is never null
        String issueDetails = (request.details != null && request.details.trim() != '') 
            ? request.details 
            : 'No details provided.';

        // ✅ Ensure JSON formatting
        String payload = '{'
            + '"channel": "' + request.slackChannel + '",'
            + '"text": "Approval Needed for High Priority Case",'
            + '"blocks": ['
                + '{'
                    + '"type": "section",'
                    + '"text": {"type": "mrkdwn", "text": "*Approval Needed: High Priority Case*"}'
                + '},'
                + '{'
                    + '"type": "section",'
                    + '"text": {"type": "mrkdwn", "text": "*Case ID:* ' + String.escapeSingleQuotes(request.recordId) 
                    + '\\n*Case Name:* ' + String.escapeSingleQuotes(request.recordName) 
                    + '\\n*Issue:* ' + String.escapeSingleQuotes(issueDetails) + '"}'
                + '},'
                + '{'
                    + '"type": "actions",'
                    + '"block_id": "approval_block_' + request.recordId + '",'
                    + '"elements": ['
                        + '{'
                            + '"type": "button",'
                            + '"text": {"type": "plain_text", "text": "Approve"},'
                            + '"style": "primary",'
                            + '"value": "approve_' + request.recordId + '",'
                            + '"action_id": "approve_action_' + request.recordId + '"'
                        + '},'
                        + '{'
                            + '"type": "button",'
                            + '"text": {"type": "plain_text", "text": "Reject"},'
                            + '"style": "danger",'
                            + '"value": "reject_' + request.recordId + '",'
                            + '"action_id": "reject_action_' + request.recordId + '"'
                        + '}'
                    + ']'
                + '}'
            + ']'
        + '}';

        Http http = new Http();
        HttpRequest httpRequest = new HttpRequest();
        httpRequest.setEndpoint(slackApiUrl);
        httpRequest.setMethod('POST');
        httpRequest.setHeader('Content-Type', 'application/json');
        httpRequest.setHeader('Authorization', 'Bearer ' + request.slackBotToken);
        httpRequest.setBody(payload);

        HttpResponse response = http.send(httpRequest);

        if (response.getStatusCode() != 200) {
            System.debug('Error sending Slack message: ' + response.getBody());
        }
    }

    public class ApprovalRequest {
        @InvocableVariable(label='Record Id' required=true)
        public String recordId;

        @InvocableVariable(label='Record Name' required=true)
        public String recordName;

        @InvocableVariable(label='Details' required=true)
        public String details;

        @InvocableVariable(label='Slack Channel ID' required=true)
        public String slackChannel;

        @InvocableVariable(label='Slack Bot Token' required=true)
        public String slackBotToken;
    }
}