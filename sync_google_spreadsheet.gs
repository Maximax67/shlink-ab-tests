/***********************************************
 * CONFIGURATION
 ***********************************************/

var PROPERTIES = PropertiesService.getScriptProperties();
var API_CONFIG = {
  baseUrl: PROPERTIES.getProperty("BASE_URL"),
  token: PROPERTIES.getProperty("API_TOKEN"),
  batchSize: PROPERTIES.getProperty("BATCH_SIZE")
};

var TABLE_CONFIG = {
  "short_urls": { 
    endpoint: "/short-urls",
    type: "full_sync", 
    idColumn: "id" 
  },
  "visits": { 
    endpoint: "/visits",
    type: "append_only", 
    idColumn: "id" 
  }
};

var METADATA_SHEET = "__sync_metadata";

/***********************************************
 * MAIN ENTRY POINT
 ***********************************************/
function syncAllTables() {
  var startTime = new Date();
  Logger.log(`=== Starting sync at ${startTime.toISOString()} ===`);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var syncMetadata = getSyncMetadata(ss);
  Logger.log(`Loaded sync metadata: ${JSON.stringify(syncMetadata)}`);

  Object.keys(TABLE_CONFIG).forEach(function(tableName) {
    var config = TABLE_CONFIG[tableName];
    
    Logger.log(`Syncing table: ${tableName} (type: ${config.type})`);
    
    if (config.type === "append_only") {
      syncAppendOnlyTable(ss, tableName, config, syncMetadata);
    } else {
      syncFullTable(ss, tableName, config, syncMetadata);
    }
  });

  saveSyncMetadata(ss, syncMetadata);
  Logger.log("Sync metadata saved.");

  var elapsed = (new Date() - startTime) / 1000;
  Logger.log(`=== Total sync completed in ${elapsed.toFixed(2)} seconds ===`);
}

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Sync Tools')
    .addItem('Run Sync', 'syncAllTables')
    .addToUi();
}

/***********************************************
 * API HELPERS
 ***********************************************/
function callSyncAPI(endpoint, params) {
  var url = API_CONFIG.baseUrl + endpoint;
  
  if (params) {
    var queryString = Object.keys(params)
      .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(params[key]))
      .join('&');
    url += '?' + queryString;
  }
  
  var options = {
    method: 'get',
    headers: {
      'X-Api-Token': API_CONFIG.token
    },
    muteHttpExceptions: true
  };
  
  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    
    if (code !== 200) {
      Logger.log(`API Error ${code}: ${response.getContentText()}`);
      throw new Error("API request failed with code " + code);
    }
    
    return JSON.parse(response.getContentText());
  } catch (e) {
    Logger.log(`Error calling API: ${e.message}`);
    throw e;
  }
}

/***********************************************
 * APPEND-ONLY SYNC (for visits)
 ***********************************************/
function syncAppendOnlyTable(ss, tableName, config, syncMetadata) {
  var tableStart = new Date();
  Logger.log(`Syncing append-only table '${tableName}'...`);

  var sheet = ss.getSheetByName(tableName);
  if (!sheet) {
    sheet = ss.insertSheet(tableName);
    Logger.log(`Created new sheet for table: ${tableName}`);
  }

  var lastSyncedId = syncMetadata[tableName] ? syncMetadata[tableName].lastId : 0;
  Logger.log(`Last synced ID for ${tableName}: ${lastSyncedId}`);

  var totalFetched = 0;
  var maxId = lastSyncedId;
  var hasMore = true;

  while (hasMore) {
    var params = {
      limit: API_CONFIG.batchSize,
      min_id: maxId
    };
    
    var result = callSyncAPI(config.endpoint, params);
    var newRows = result.data;
    
    Logger.log(`Fetched ${newRows.length} records from API`);

    if (newRows.length === 0) {
      hasMore = false;
      break;
    }

    var header = sheet.getLastRow() === 0 ? null : sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    
    if (!header) {
      header = getHeaderFromObjects(newRows);
      sheet.getRange(1, 1, 1, header.length).setValues([header]);
      Logger.log(`Inserted header for sheet: ${tableName}`);
    }

    var rowsToInsert = newRows.map(function(record) {
      return header.map(function(col) {
        var value = getNestedValue(record, col);
        return value !== null && value !== undefined ? value : "";
      });
    });

    if (rowsToInsert.length > 0) {
      var startRow = sheet.getLastRow() + 1;
      sheet.getRange(startRow, 1, rowsToInsert.length, rowsToInsert[0].length).setValues(rowsToInsert);
      Logger.log(`Appended ${rowsToInsert.length} rows to sheet: ${tableName}`);
      totalFetched += rowsToInsert.length;

      var idIndex = header.indexOf(config.idColumn);
      if (idIndex !== -1) {
        rowsToInsert.forEach(function(row) {
          var currentId = parseInt(row[idIndex]);
          if (currentId > maxId) maxId = currentId;
        });
      }
    }

    if (newRows.length < API_CONFIG.batchSize) {
      hasMore = false;
    }
  }

  if (!syncMetadata[tableName]) syncMetadata[tableName] = {};
  syncMetadata[tableName].lastId = maxId;
  syncMetadata[tableName].lastSync = new Date().toISOString();

  var elapsed = (new Date() - tableStart) / 1000;
  Logger.log(`Append-only table '${tableName}' sync finished in ${elapsed.toFixed(2)}s (${totalFetched} total rows)`);
}

/***********************************************
 * FULL SYNC (for short_urls)
 ***********************************************/
function syncFullTable(ss, tableName, config, syncMetadata) {
  var tableStart = new Date();
  Logger.log(`Loading full-sync table '${tableName}'...`);

  var sheet = ss.getSheetByName(tableName);
  if (!sheet) sheet = ss.insertSheet(tableName);

  var allRecords = [];
  var offset = 0;
  var hasMore = true;

  while (hasMore) {
    var params = {
      limit: API_CONFIG.batchSize,
      offset: offset
    };
    
    var result = callSyncAPI(config.endpoint, params);
    allRecords = allRecords.concat(result.data);
    
    Logger.log(`Fetched ${result.data.length} records (offset: ${offset}, total so far: ${allRecords.length})`);
    
    offset += result.data.length;
    
    if (result.data.length < API_CONFIG.batchSize || offset >= result.total) {
      hasMore = false;
    }
  }

  Logger.log(`Total records fetched from API: ${allRecords.length}`);

  sheet.clear();
  
  if (allRecords.length > 0) {
    var header = getHeaderFromObjects(allRecords);
    var rows = [header];
    
    allRecords.forEach(function(record) {
      rows.push(header.map(function(col) {
        var value = getNestedValue(record, col);
        return value !== null && value !== undefined ? value : "";
      }));
    });

    sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    Logger.log(`Wrote ${rows.length - 1} rows to sheet ${tableName}`);
  }

  if (!syncMetadata[tableName]) syncMetadata[tableName] = {};
  syncMetadata[tableName].lastSync = new Date().toISOString();
  syncMetadata[tableName].recordCount = allRecords.length;

  var elapsed = (new Date() - tableStart) / 1000;
  Logger.log(`Full-sync table '${tableName}' finished in ${elapsed.toFixed(2)}s`);
}

/***********************************************
 * HELPER FUNCTIONS
 ***********************************************/
function getHeaderFromObjects(records) {
  var headers = new Set();

  function extractKeys(obj, prefix) {
    Object.keys(obj).forEach(function(key) {
      var fullKey = prefix ? prefix + '.' + key : key;
      if (obj[key] !== null && typeof obj[key] === 'object' && !Array.isArray(obj[key])) {
        extractKeys(obj[key], fullKey);
      } else {
        headers.add(fullKey);
      }
    });
  }

  records.forEach(function(record) {
    extractKeys(record, '');
  });

  return Array.from(headers);
}

function getNestedValue(obj, path) {
  return path.split('.').reduce(function(current, key) {
    return current ? current[key] : null;
  }, obj);
}

/***********************************************
 * METADATA
 ***********************************************/
function getSyncMetadata(ss) {
  var sheet = ss.getSheetByName(METADATA_SHEET);
  if (!sheet) return {};
  var lastRow = sheet.getLastRow();
  if (lastRow <= 1) return {};
  var data = sheet.getRange(2, 1, lastRow - 1, 4).getValues();
  var metadata = {};
  for (var i = 0; i < data.length; i++) {
    var t = data[i];
    if (t[0]) {
      metadata[t[0]] = {
        lastId: t[1] || 0,
        recordCount: t[2] || 0,
        lastSync: t[3] || ""
      };
    }
  }
  return metadata;
}

function saveSyncMetadata(ss, metadata) {
  var sheet = ss.getSheetByName(METADATA_SHEET) || ss.insertSheet(METADATA_SHEET);
  sheet.clearContents();
  sheet.getRange(1, 1, 1, 4).setValues([["table_name", "last_id", "record_count", "last_sync"]]);
  var rows = [];
  Object.keys(metadata).forEach(function(t) {
    var m = metadata[t];
    rows.push([t, m.lastId || 0, m.recordCount || 0, m.lastSync || ""]);
  });
  if (rows.length > 0) sheet.getRange(2, 1, rows.length, 4).setValues(rows);
  Logger.log(`Saved metadata for ${rows.length} tables`);
}
