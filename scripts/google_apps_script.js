/**
 * VedaVMS Google Sheet Automation Suite (Google Apps Script)
 * 
 * Provides a custom menu in Google Sheets with live status tracking:
 *  - 🚀 Publish to Staging (new.vedavms.in)  -> updates Cell J2
 *  - 🔴 Publish to Production (vedavms.in)  -> updates Cell J3
 */

const REPO_OWNER = 'sekharnarayanaswamy-del';
const REPO_NAME = 'VedaVMS';

function getGitHubToken() {
  var prop = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (prop && prop.trim() !== '') return prop.trim();
  return 'PASTE_YOUR_GITHUB_TOKEN_HERE';
}

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 VedaVMS')
    .addItem('🚀 Publish to Staging (new.vedavms.in)', 'triggerStagingDeploy')
    .addSeparator()
    .addItem('🔴 Publish to Production (vedavms.in)', 'triggerProductionDeploy')
    .addToUi();
}

function monitorWorkflowRun(workflowFile, targetName, targetUrl, isProduction) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();
  var token = getGitHubToken();

  ss.toast('Deployment triggered on GitHub Actions. Waiting for completion...', '🚀 VedaVMS', 15);
  Utilities.sleep(3000);

  var runsUrl = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/' + workflowFile + '/runs?per_page=1';
  var headers = {
    'Authorization': 'token ' + token,
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Google-Apps-Script-VedaVMS'
  };

  var runId = null;
  var maxWaitSeconds = 180;
  var elapsed = 0;
  var checkInterval = 5;

  while (elapsed < maxWaitSeconds) {
    try {
      var resp = UrlFetchApp.fetch(runsUrl, { method: 'get', headers: headers, muteHttpExceptions: true });
      if (resp.getResponseCode() === 200) {
        var data = JSON.parse(resp.getContentText());
        if (data.workflow_runs && data.workflow_runs.length > 0) {
          var latest = data.workflow_runs[0];
          runId = latest.id;
          var status = latest.status;
          var conclusion = latest.conclusion;

          if (status === 'completed') {
            if (conclusion === 'success') {
              // Format timestamp: DD-MMM-YYYY, hh:mm:ss a IST
              var now = new Date();
              var nowStr = Utilities.formatDate(now, "Asia/Kolkata", "dd-MMM-yyyy, hh:mm:ss a 'IST'");

              try {
                var sheet = ss.getActiveSheet();
                sheet.getRange("J1").setValue("Publish Status").setFontWeight("bold");

                if (!isProduction) {
                  // Staging in J2
                  sheet.getRange("J2")
                    .setValue("🟡 Staging: " + nowStr)
                    .setFontWeight("normal")
                    .setBackground("#FFF2CC")
                    .setFontColor("#7F6000");
                } else {
                  // Production in J3
                  sheet.getRange("J3")
                    .setValue("🟢 Production: " + nowStr)
                    .setFontWeight("normal")
                    .setBackground("#E6F4EA")
                    .setFontColor("#137333");
                }
                SpreadsheetApp.flush();
              } catch (ex) {}

              ui.alert(
                '🎉 Deployment Successful!',
                'The website has been published to ' + targetName + ' successfully!\n\n' +
                '• Live URL: ' + targetUrl + '\n' +
                '• Completed in: ' + elapsed + ' seconds\n' +
                '• Timestamp logged to: ' + (isProduction ? 'Cell J3' : 'Cell J2') + '\n\n' +
                '💡 Note: If your browser still shows the old page, press Ctrl + F5 (or Cmd + Shift + R) to hard-refresh.',
                ui.ButtonSet.OK
              );
              return;
            } else {
              ui.alert(
                '❌ Deployment Failed (' + conclusion + ')',
                'GitHub Actions encountered an issue during deployment.\n\n' +
                '• Run ID: ' + runId + '\n' +
                '• View Run Logs: ' + latest.html_url,
                ui.ButtonSet.OK
              );
              return;
            }
          }
        }
      }
    } catch (e) {}

    Utilities.sleep(checkInterval * 1000);
    elapsed += checkInterval;
  }

  ui.alert(
    '⏳ Deployment Still Processing',
    'The build was dispatched and is running on GitHub Actions. It should finish shortly.\n\nCheck live status at: ' + targetUrl,
    ui.ButtonSet.OK
  );
}

function triggerStagingDeploy() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.alert(
    '🚀 Publish to Staging',
    'Are you sure you want to rebuild and publish all changes to the staging website (https://new.vedavms.in)?',
    ui.ButtonSet.YES_NO
  );

  if (response != ui.Button.YES) return;

  var token = getGitHubToken();
  if (!token || token === 'PASTE_YOUR_GITHUB_TOKEN_HERE') {
    ui.alert('❌ Error: GITHUB_TOKEN is not configured in Script Properties.');
    return;
  }

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/deploy_staging.yml/dispatches';
  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Google-Apps-Script-VedaVMS'
    },
    payload: JSON.stringify({ ref: 'main' }),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      monitorWorkflowRun('deploy_staging.yml', 'Staging (new.vedavms.in)', 'https://new.vedavms.in', false);
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}

function triggerProductionDeploy() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.alert(
    '🔴 WARNING: Live Production Rollout',
    'Are you sure you want to rebuild and publish all changes directly to LIVE PRODUCTION (https://vedavms.in)?\n\nThis will update the public website.',
    ui.ButtonSet.YES_NO
  );

  if (response != ui.Button.YES) return;

  var token = getGitHubToken();
  if (!token || token === 'PASTE_YOUR_GITHUB_TOKEN_HERE') {
    ui.alert('❌ Error: GITHUB_TOKEN is not configured in Script Properties.');
    return;
  }

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/deploy_production.yml/dispatches';
  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Google-Apps-Script-VedaVMS'
    },
    payload: JSON.stringify({ ref: 'main', inputs: { confirm_deploy: 'DEPLOY' } }),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      monitorWorkflowRun('deploy_production.yml', 'Production (vedavms.in)', 'https://vedavms.in', true);
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}
