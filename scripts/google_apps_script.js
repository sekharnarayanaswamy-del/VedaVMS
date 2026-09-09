/**
 * VedaVMS Google Sheet Automation Suite (Google Apps Script)
 * 
 * Provides a custom menu in Google Sheets:
 *  - 🚀 Publish to Staging (new.vedavms.in)
 *  - 🔴 Publish to Production (vedavms.in)
 * 
 * Features:
 *  - Real-time progress tracking with Google Sheets toast notifications
 *  - Live polling of GitHub Actions run status until complete
 *  - Instant confirmation popup showing whether the deployment succeeded or failed
 *  - Automatic logging of last deployment timestamp in the spreadsheet
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

/**
 * Polls GitHub Actions workflow run until completion and reports final status.
 */
function monitorWorkflowRun(workflowFile, targetName, targetUrl, cellCoord) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();
  var token = getGitHubToken();

  ss.toast('Connecting to GitHub Actions...', '🚀 VedaVMS Pipeline', 5);
  Utilities.sleep(3000);

  var runsUrl = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/' + workflowFile + '/runs?per_page=1';
  var headers = {
    'Authorization': 'token ' + token,
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Google-Apps-Script-VedaVMS'
  };

  var runId = null;
  var maxWaitSeconds = 120;
  var elapsed = 0;
  var checkInterval = 4;

  // Poll until run finishes
  while (elapsed < maxWaitSeconds) {
    try {
      var resp = UrlFetchApp.fetch(runsUrl, { method: 'get', headers: headers, muteHttpExceptions: true });
      if (resp.getResponseCode() === 200) {
        var data = JSON.parse(resp.getContentText());
        if (data.workflow_runs && data.workflow_runs.length > 0) {
          var latest = data.workflow_runs[0];
          runId = latest.id;
          var status = latest.status;         // 'queued', 'in_progress', 'completed'
          var conclusion = latest.conclusion; // 'success', 'failure', etc.

          if (status === 'queued') {
            ss.toast('Waiting in GitHub queue (' + elapsed + 's)...', '⏳ ' + targetName, checkInterval + 1);
          } else if (status === 'in_progress') {
            ss.toast('Generating HTML & deploying via FTPS (' + elapsed + 's)...', '⚙️ ' + targetName, checkInterval + 1);
          } else if (status === 'completed') {
            if (conclusion === 'success') {
              // Log timestamp in cell
              try {
                var sheet = ss.getActiveSheet();
                if (cellCoord) {
                  var nowStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");
                  sheet.getRange(cellCoord).setValue('Last ' + targetName + ': ' + nowStr);
                }
              } catch (ex) {}

              ui.alert(
                '🎉 Deployment Successful!',
                'The changes have been published to ' + targetName + ' successfully!\n\n' +
                '• Live URL: ' + targetUrl + '\n' +
                '• Completed in: ' + elapsed + ' seconds\n' +
                '• GitHub Run ID: ' + runId,
                ui.ButtonSet.OK
              );
              return;
            } else {
              ui.alert(
                '❌ Deployment Failed (' + conclusion + ')',
                'GitHub Actions encountered an issue during deployment.\n\n' +
                '• Run ID: ' + runId + '\n' +
                '• Logs: ' + latest.html_url,
                ui.ButtonSet.OK
              );
              return;
            }
          }
        }
      }
    } catch (e) {
      // Continue polling on transient fetch glitch
    }

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
    ui.alert('❌ Error: GITHUB_TOKEN is not configured.\n\nPlease open Extensions > Apps Script > Project Settings (gear icon) > Script Properties and add GITHUB_TOKEN.');
    return;
  }

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/deploy_staging.yml/dispatches';
  var payload = { ref: 'main' };

  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Google-Apps-Script-VedaVMS'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      // Start live monitoring
      monitorWorkflowRun('deploy_staging.yml', 'Staging (new.vedavms.in)', 'https://new.vedavms.in', 'J2');
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
    ui.alert('❌ Error: GITHUB_TOKEN is not configured.\n\nPlease open Extensions > Apps Script > Project Settings (gear icon) > Script Properties and add GITHUB_TOKEN.');
    return;
  }

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/deploy_production.yml/dispatches';
  var payload = {
    ref: 'main',
    inputs: { confirm_deploy: 'DEPLOY' }
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Google-Apps-Script-VedaVMS'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      // Start live monitoring
      monitorWorkflowRun('deploy_production.yml', 'Production (vedavms.in)', 'https://vedavms.in', 'J3');
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}
