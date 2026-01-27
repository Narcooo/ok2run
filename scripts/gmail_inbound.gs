// Gmail inbound forwarder for Approval Gate.
// Configure Script Properties:
//   APPROVAL_GATE_URL = https://<public-host>/v1/inbox/email-reply
//   APPROVAL_API_KEY = <your api key>
//   GMAIL_QUERY = is:unread subject:(appr_)

function processApprovalReplies() {
  var props = PropertiesService.getScriptProperties();
  var endpoint = props.getProperty('APPROVAL_GATE_URL');
  var apiKey = props.getProperty('APPROVAL_API_KEY');
  var query = props.getProperty('GMAIL_QUERY') || 'is:unread subject:(appr_)';

  if (!endpoint || !apiKey) {
    throw new Error('Missing script properties: APPROVAL_GATE_URL / APPROVAL_API_KEY');
  }

  if (!endpoint.match(/\/v1\/inbox\/email-reply$/)) {
    endpoint = endpoint.replace(/\/+$/, '') + '/v1/inbox/email-reply';
  }

  var threads = GmailApp.search(query, 0, 20);
  for (var i = 0; i < threads.length; i++) {
    var messages = threads[i].getMessages();
    for (var j = 0; j < messages.length; j++) {
      var msg = messages[j];
      if (msg.isUnread()) {
        var payload = {
          subject: msg.getSubject(),
          body: msg.getPlainBody()
        };
        var options = {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          headers: { Authorization: 'Bearer ' + apiKey },
          muteHttpExceptions: true
        };
        var resp = UrlFetchApp.fetch(endpoint, options);
        if (resp.getResponseCode() >= 200 && resp.getResponseCode() < 300) {
          msg.markRead();
        } else {
          Logger.log('Failed to forward message: ' + resp.getContentText());
        }
      }
    }
  }
}
