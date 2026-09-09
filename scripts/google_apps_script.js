/**
 * VedaVMS Google Sheet Automation Suite (Google Apps Script)
 * 
 * Provides a custom menu in Google Sheets:
 *  - 🚀 Publish to Staging (new.vedavms.in)
 *  - 🔴 Publish to Production (vedavms.in)
 * 
 * Installation Instructions:
 *  1. In your Google Sheet, click Extensions > Apps Script.
 *  2. Replace existing code with this file.
 *  3. In Project Settings (gear icon), click "Add script property" -> Name: GITHUB_TOKEN -> Value: (your GitHub Token).
 *  4. Click Save, then refresh your Google Sheet.
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

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/dispatches';
  var payload = {
    event_type: 'deploy_staging'
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
      ui.alert('✅ Success! Staging deployment has started.\n\nThe website will be updated in ~1 minute at https://new.vedavms.in');
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

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/dispatches';
  var payload = {
    event_type: 'deploy_production'
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
      ui.alert('✅ Success! Production deployment has started.\n\nThe live site will be updated in ~1 minute at https://vedavms.in');
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}
