/**
 * VedaVMS Google Sheet Automation Suite (Google Apps Script)
 * 
 * Provides a custom menu in Google Sheets with Semantic Versioning & live status tracking:
 *  - 🚀 Publish to Staging (new.vedavms.in)  -> updates Cell J2
 *  - 🔴 Publish to Production (vedavms.in)  -> auto-increments Patch version in Cell J1, updates Cell J3
 *  - 🏷️ Set / Bump Catalog Version...       -> allows manual major/minor/custom version bumping
 *  - 📋 Setup Sheet Status Headers (I1:J3)   -> formats Cells I1:J3
 */

const REPO_OWNER = 'sekharnarayanaswamy-del';
const REPO_NAME = 'VedaVMS';
const DEFAULT_VERSION = '2.5.0';

function getGitHubToken() {
  var prop = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (prop && prop.trim() !== '') return prop.trim();
  return 'PASTE_YOUR_GITHUB_TOKEN_HERE';
}

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 VedaVMS')
    .addItem('🚀 Publish to Staging (new.vedavms.in)', 'triggerStagingDeploy')
    .addItem('🔴 Publish to Production (vedavms.in)', 'triggerProductionDeploy')
    .addSeparator()
    .addItem('🏷️ Set / Bump Catalog Version...', 'promptSetVersion')
    .addItem('📋 Setup Sheet Status Headers (I1:J3)', 'setupStatusHeaders')
    .addToUi();
}

/**
 * Get the master sheet (targets 'vedavms_documents' or active sheet)
 */
function getMasterSheet(ss) {
  if (!ss) ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("vedavms_documents");
  if (!sheet) {
    sheet = ss.getActiveSheet() || ss.getSheets()[0];
  }
  return sheet;
}

/**
 * Clean and normalize a version string (e.g., 'v2.5.0' -> '2.5.0')
 */
function cleanVersion(ver) {
  if (!ver) return DEFAULT_VERSION;
  var str = ver.toString().trim();
  var match = str.match(/(\d+\.\d+\.\d+)/);
  return match ? match[1] : DEFAULT_VERSION;
}

/**
 * Increment the patch version (e.g. 2.5.0 -> 2.5.1)
 */
function incrementPatchVersion(ver) {
  var clean = cleanVersion(ver);
  var parts = clean.split('.');
  var major = parseInt(parts[0], 10) || 2;
  var minor = parseInt(parts[1], 10) || 5;
  var patch = (parseInt(parts[2], 10) || 0) + 1;
  return major + '.' + minor + '.' + patch;
}

/**
 * Increment the minor version (e.g. 2.5.0 -> 2.6.0)
 */
function incrementMinorVersion(ver) {
  var clean = cleanVersion(ver);
  var parts = clean.split('.');
  var major = parseInt(parts[0], 10) || 2;
  var minor = (parseInt(parts[1], 10) || 5) + 1;
  return major + '.' + minor + '.0';
}

/**
 * Increment the major version (e.g. 2.5.0 -> 3.0.0)
 */
function incrementMajorVersion(ver) {
  var clean = cleanVersion(ver);
  var parts = clean.split('.');
  var major = (parseInt(parts[0], 10) || 2) + 1;
  return major + '.0.0';
}

/**
 * Get the current catalog version from the master sheet (Cell J1)
 */
function getCatalogVersion() {
  try {
    var sheet = getMasterSheet();
    var val = sheet.getRange("J1").getValue();
    return cleanVersion(val);
  } catch (e) {
    return DEFAULT_VERSION;
  }
}

/**
 * Update the catalog version badge in Cell I1:J1
 */
function setCatalogVersion(versionStr) {
  var clean = cleanVersion(versionStr);
  try {
    var sheet = getMasterSheet();
    
    // Format I1 label
    sheet.getRange("I1")
      .setValue("Catalog Version:")
      .setFontWeight("bold")
      .setHorizontalAlignment("right");
    
    // Format J1 version badge
    sheet.getRange("J1")
      .setValue("v" + clean)
      .setFontWeight("bold")
      .setHorizontalAlignment("center")
      .setBackground("#E8F0FE")
      .setFontColor("#1967D2");
      
    SpreadsheetApp.flush();
  } catch (e) {}
  return clean;
}

/**
 * Set up / format cells I1:J3 with status labels and version badge
 */
function setupStatusHeaders() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = getMasterSheet(ss);
  var currentVer = getCatalogVersion();

  // Row 1: Version
  sheet.getRange("I1").setValue("Catalog Version:").setFontWeight("bold").setHorizontalAlignment("right");
  sheet.getRange("J1")
    .setValue("v" + currentVer)
    .setFontWeight("bold")
    .setHorizontalAlignment("center")
    .setBackground("#E8F0FE")
    .setFontColor("#1967D2");

  // Row 2: Staging Status
  sheet.getRange("I2").setValue("Staging Status:").setFontWeight("bold").setHorizontalAlignment("right");
  var j2Val = sheet.getRange("J2").getValue();
  if (!j2Val || j2Val.toString().trim() === "") {
    sheet.getRange("J2")
      .setValue("🟡 Staging: Not deployed yet")
      .setFontWeight("normal")
      .setBackground("#FFF2CC")
      .setFontColor("#7F6000");
  }

  // Row 3: Production Status
  sheet.getRange("I3").setValue("Production Status:").setFontWeight("bold").setHorizontalAlignment("right");
  var j3Val = sheet.getRange("J3").getValue();
  if (!j3Val || j3Val.toString().trim() === "") {
    sheet.getRange("J3")
      .setValue("🟢 Production: Not deployed yet")
      .setFontWeight("normal")
      .setBackground("#E6F4EA")
      .setFontColor("#137333");
  }

  // Column auto-fit & aesthetics
  sheet.setColumnWidth(9, 140);  // Column I
  sheet.setColumnWidth(10, 320); // Column J
  SpreadsheetApp.flush();

  SpreadsheetApp.getUi().alert(
    '✅ Setup Complete',
    'Status headers (Cells I1:J3) and Catalog Version v' + currentVer + ' are configured and formatted on the catalog sheet.',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/**
 * Interactive UI prompt to set or bump version
 */
function promptSetVersion() {
  var ui = SpreadsheetApp.getUi();
  var current = getCatalogVersion();
  var nextPatch = incrementPatchVersion(current);
  var nextMinor = incrementMinorVersion(current);
  var nextMajor = incrementMajorVersion(current);

  var promptText = 'Current Catalog Version: v' + current + '\n\n' +
    'Enter the new semantic version (e.g. ' + nextPatch + ', ' + nextMinor + ', or ' + nextMajor + '):';

  var res = ui.prompt('🏷️ Set / Bump Catalog Version', promptText, ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;

  var input = res.getResponseText().trim();
  if (!input) return;

  var clean = cleanVersion(input);
  setCatalogVersion(clean);

  ui.alert(
    '✅ Version Updated',
    'Catalog version set to: v' + clean + '\n\nCell J1 updated on the master sheet.',
    ui.ButtonSet.OK
  );
}

/**
 * Monitor GitHub Actions workflow run and update Google Sheet cells upon completion
 */
function monitorWorkflowRun(workflowFile, targetName, targetUrl, isProduction, versionStr) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();
  var token = getGitHubToken();

  ss.toast('Deployment triggered on GitHub Actions for v' + versionStr + '... Waiting for completion.', '🚀 VedaVMS', 15);
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
                var sheet = getMasterSheet(ss);
                setCatalogVersion(versionStr);

                if (!isProduction) {
                  // Staging in J2
                  sheet.getRange("I2").setValue("Staging Status:").setFontWeight("bold").setHorizontalAlignment("right");
                  sheet.getRange("J2")
                    .setValue("🟡 Staging: " + nowStr + " (v" + versionStr + ")")
                    .setFontWeight("normal")
                    .setBackground("#FFF2CC")
                    .setFontColor("#7F6000");
                } else {
                  // Production in J3
                  sheet.getRange("I3").setValue("Production Status:").setFontWeight("bold").setHorizontalAlignment("right");
                  sheet.getRange("J3")
                    .setValue("🟢 Production: " + nowStr + " (v" + versionStr + ")")
                    .setFontWeight("normal")
                    .setBackground("#E6F4EA")
                    .setFontColor("#137333");
                }
                SpreadsheetApp.flush();
              } catch (ex) {}

              ui.alert(
                '🎉 Deployment Successful!',
                'The website has been published to ' + targetName + ' successfully!\n\n' +
                '• Catalog Version: v' + versionStr + '\n' +
                '• Live URL: ' + targetUrl + '\n' +
                '• Completed in: ' + elapsed + ' seconds\n' +
                '• Status logged to: ' + (isProduction ? 'Cell J3' : 'Cell J2') + '\n\n' +
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
    'The build for v' + versionStr + ' was dispatched and is running on GitHub Actions. It should finish shortly.\n\nCheck live status at: ' + targetUrl,
    ui.ButtonSet.OK
  );
}

/**
 * Trigger deployment to Staging (new.vedavms.in)
 */
function triggerStagingDeploy() {
  var ui = SpreadsheetApp.getUi();
  var currentVer = getCatalogVersion();

  var response = ui.alert(
    '🚀 Publish to Staging (v' + currentVer + ')',
    'Are you sure you want to rebuild and publish all changes to the staging website (https://new.vedavms.in)?\n\n' +
    '• Catalog Version: v' + currentVer + '\n' +
    '• Target: https://new.vedavms.in',
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
    payload: JSON.stringify({ ref: 'main', inputs: { catalog_version: currentVer } }),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      monitorWorkflowRun('deploy_staging.yml', 'Staging (new.vedavms.in)', 'https://new.vedavms.in', false, currentVer);
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}

/**
 * Trigger deployment to Live Production (vedavms.in) with automatic Semantic Patch Version increment
 */
function triggerProductionDeploy() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var currentVer = getCatalogVersion();
  var nextVer = incrementPatchVersion(currentVer);

  var response = ui.alert(
    '🔴 WARNING: Live Production Rollout & Version Bump',
    'Are you sure you want to rebuild and publish all changes directly to LIVE PRODUCTION (https://vedavms.in)?\n\n' +
    '🏷️ Semantic Version Bump:\n' +
    '  • Current Version: v' + currentVer + '\n' +
    '  • New Release Version: v' + nextVer + '\n\n' +
    'This will increment the catalog patch version to v' + nextVer + ', stamp all pages, and publish to https://vedavms.in.',
    ui.ButtonSet.YES_NO
  );

  if (response != ui.Button.YES) return;

  var token = getGitHubToken();
  if (!token || token === 'PASTE_YOUR_GITHUB_TOKEN_HERE') {
    ui.alert('❌ Error: GITHUB_TOKEN is not configured in Script Properties.');
    return;
  }

  // Pre-update the version cell immediately and show toast
  setCatalogVersion(nextVer);
  ss.toast('Catalog version bumped to v' + nextVer + ' in Cell J1. Dispatching build...', '🚀 VedaVMS', 5);

  var url = 'https://api.github.com/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/deploy_production.yml/dispatches';
  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'token ' + token,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Google-Apps-Script-VedaVMS'
    },
    payload: JSON.stringify({
      ref: 'main',
      inputs: {
        confirm_deploy: 'DEPLOY',
        catalog_version: nextVer
      }
    }),
    muteHttpExceptions: true
  };

  try {
    var resp = UrlFetchApp.fetch(url, options);
    var code = resp.getResponseCode();
    if (code === 204 || code === 200) {
      monitorWorkflowRun('deploy_production.yml', 'Production (vedavms.in)', 'https://vedavms.in', true, nextVer);
    } else {
      ui.alert('❌ GitHub API Error (HTTP ' + code + '):\n' + resp.getContentText());
    }
  } catch (e) {
    ui.alert('❌ Error: ' + e.toString());
  }
}
