@RestResource(urlMapping='/ApprovalResponse/*')
global with sharing class ApprovalResponse {

    @HttpPost
    global static String processApproval() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            // Parse request body
            String requestBody = req.requestBody.toString();
            Map<String, Object> data = (Map<String, Object>) JSON.deserializeUntyped(requestBody);

            String recordId = (String) data.get('recordId');
            String decision = (String) data.get('decision');
            String userEmail = (String) data.get('userEmail');

            // Validate input
            if (String.isEmpty(recordId) || String.isEmpty(decision) || String.isEmpty(userEmail)) {
                res.statusCode = 400;
                return '{"status": "error", "message": "Missing required parameters"}';
            }

            // Retrieve Case
            Case c = [SELECT Id, Status, Priority FROM Case WHERE Id = :recordId LIMIT 1];

            if (decision == 'Approved') {
                c.Status = 'In Progress';
            } else if (decision == 'Rejected') {
                c.Status = 'New';
                c.Priority = 'Medium';
            } else {
                res.statusCode = 400;
                return '{"status": "error", "message": "Invalid decision value"}';
            }

            update c;

            res.statusCode = 200;
            return '{"status": "success", "message": "Case updated successfully"}';

        } catch (Exception e) {
            res.statusCode = 500;
            return '{"status": "error", "message": "' + e.getMessage() + '"}';
        }
    }
}