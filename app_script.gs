/**
 * Apps Script Web App: return mapping of question title -> entry.{id}
 *
 * How to use:
 * 1. Paste into a new standalone Apps Script project.
 * 2. Run setApiTokenOnce_('your-secret-token') once from the editor or
 *    set the property manually in Project Settings -> Script properties.
 * 3. Deploy -> New deployment -> Web app
 *    - Execute as: Me (script owner)
 *    - Who has access: Anyone (or Anyone with Google account) depending on security
 *
 * Example call (GET):
 *  GET https://script.google.com/macros/s/DEPLOY_ID/exec?formId=FORM_ID&token=your-secret-token
 *
 * Example call (curl):
 *  curl "https://script.google.com/macros/s/DEPLOY_ID/exec?formId=FORM_ID&token=your-secret-token"
 */

/**
 * GET handler
 */
function doGet(e) {
  return handleRequest_(e);
}

/**
 * POST handler (accepts formId & token as form-encoded or JSON body)
 */
function doPost(e) {
  return handleRequest_(e);
}

/**
 * Central request handler
 */
function handleRequest_(e) {
  try {
    const params = normalizeParams_(e);
    const formId = params.formId;
    const token = params.token;

    if (!formId) {
      return jsonResponse_({ error: 'Missing parameter: formId' }, 400);
    }

    // Validate token against the value stored in Script Properties
    const expected = PropertiesService.getScriptProperties().getProperty('API_TOKEN');
    if (!expected) {
      return jsonResponse_({ error: 'API_TOKEN not configured. Run setApiTokenOnce_(token) in Apps Script editor or set Script Properties.' }, 500);
    }
    if (!token || token !== expected) {
      return jsonResponse_({ error: 'Unauthorized: invalid token' }, 401);
    }

    // Open the form (script owner must have Editor access)
    const form = FormApp.openById(formId);

        // Collect items and add default responses for prefillable items
    const items = form.getItems();
    const response = form.createResponse();
    const records = []; // { title, itemId, type, entryId, _defaultResponse }

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const defaultResponse = getDefaultItemResponse_(item);
      records.push({
        title: item.getTitle ? item.getTitle() : '',
        itemId: item.getId ? item.getId().toString() : null,
        type: item.getType ? item.getType().toString() : null,
        entryId: null,                // to be filled per-item below
        _defaultResponse: defaultResponse  // store the actual ItemResponse (or null)
      });
      if (defaultResponse) {
        // add to the big response so prefilledUrl includes them (optional)
        response.withItemResponse(defaultResponse);
      }
    }

    // If you still want the full prefilled URL that includes all added responses:
    const prefilledUrl = response.toPrefilledUrl();

    // --- New robust approach: for each item that had a default response,
    // create a single-item prefilled URL and extract its entry.<digits> ID ---
    const singleRe = /[?&]entry\.([0-9]+)=/;
    for (let i = 0; i < records.length; i++) {
      const rec = records[i];
      if (rec._defaultResponse) {
        try {
          // create a response that only includes this one item response
          const singleUrl = form.createResponse()
            .withItemResponse(rec._defaultResponse)
            .toPrefilledUrl();

          const m = singleRe.exec(singleUrl);
          rec.entryId = m ? m[1] : null;
        } catch (err) {
          // something went wrong with this item; leave entryId null
          rec.entryId = null;
        }
      } else {
        rec.entryId = null;
      }
      // remove the helper to keep output clean
      delete rec._defaultResponse;
    }

    return jsonResponse_({
      formId: formId,
      prefilledUrl: prefilledUrl,
      mapping: records
    }, 200);

  } catch (err) {
    return jsonResponse_({ error: err.message, stack: err.stack }, 500);
  }
}

/**
 * Produce a ContentService JSON response with proper HTTP status (Apps Script mimics)
 */
function jsonResponse_(obj, statusCode) {
  // ContentService does not natively let us set HTTP status code,
  // but we include it in the payload for clients that expect it.
  const payload = Object.assign({ status: statusCode || 200 }, obj);
  return ContentService.createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Normalize parameters from GET query, POST form data, or JSON body
 */
function normalizeParams_(e) {
  // e.parameter contains query params for GET and form-encoded POST
  const p = {};
  if (e && e.parameter) {
    for (const k in e.parameter) {
      p[k] = e.parameter[k];
    }
  }
  // If POST with JSON body, e.postData.contents holds the raw JSON
  if (e && e.postData && e.postData.type === 'application/json' && e.postData.contents) {
    try {
      const body = JSON.parse(e.postData.contents);
      for (const k in body) {
        p[k] = body[k];
      }
    } catch (err) {
      // ignore JSON parse error; we'll rely on query/form params
    }
  }
  return p;
}

/**
 * Create a default item response for an item so it appears in prefilled URL.
 * Return null for items that can't be prefilled or are unsupported.
 */
function getDefaultItemResponse_(item) {
  try {
    const type = item.getType();
    switch (type) {
      case FormApp.ItemType.TEXT:
        return item.asTextItem().createResponse('x');
      case FormApp.ItemType.PARAGRAPH_TEXT:
        return item.asParagraphTextItem().createResponse('x');
      case FormApp.ItemType.MULTIPLE_CHOICE: {
        const choices = item.asMultipleChoiceItem().getChoices();
        if (choices && choices.length) {
          return item.asMultipleChoiceItem().createResponse(choices[0].getValue());
        }
        return null;
      }
      case FormApp.ItemType.CHECKBOX: {
        const choices = item.asCheckboxItem().getChoices();
        if (choices && choices.length) {
          return item.asCheckboxItem().createResponse([choices[0].getValue()]);
        }
        return null;
      }
      case FormApp.ItemType.LIST: {
        const choices = item.asListItem().getChoices();
        if (choices && choices.length) {
          return item.asListItem().createResponse(choices[0].getValue());
        }
        return null;
      }
      case FormApp.ItemType.SCALE:
        return item.asScaleItem().createResponse(item.asScaleItem().getLowerBound());
      case FormApp.ItemType.GRID: {
        const columns = item.asGridItem().getColumns();
        const rows = item.asGridItem().getRows();
        if (columns && columns.length && rows && rows.length) {
          // choose first column for every row
          const resp = rows.map(() => columns[0]);
          return item.asGridItem().createResponse(resp);
        }
        return null;
      }
      case FormApp.ItemType.CHECKBOX_GRID: {
        const columns = item.asCheckboxGridItem().getColumns();
        const rows = item.asCheckboxGridItem().getRows();
        if (columns && columns.length && rows && rows.length) {
          const resp = rows.map(() => [columns[0]]);
          return item.asCheckboxGridItem().createResponse(resp);
        }
        return null;
      }
      case FormApp.ItemType.DATE:
        return item.asDateItem().createResponse(new Date());
      case FormApp.ItemType.TIME:
        // createResponse(hour, minute)
        return item.asTimeItem().createResponse(0, 0);
      case FormApp.ItemType.DATETIME:
        return item.asDateTimeItem().createResponse(new Date());
      case FormApp.ItemType.DURATION:
        // hours, minutes, seconds
        return item.asDurationItem().createResponse(0, 0, 0);
      // The following types are not prefillable (or not meaningful for prefilled URL)
      case FormApp.ItemType.SECTION_HEADER:
      case FormApp.ItemType.PAGE_BREAK:
      case FormApp.ItemType.IMAGE:
      case FormApp.ItemType.VIDEO:
      case FormApp.ItemType.FILE_UPLOAD:
      default:
        return null;
    }
  } catch (err) {
    // If any item specific call fails, skip this item (return null)
    return null;
  }
}

/**
 * Utility: set API token once from script editor (run manually)
 * Example: setApiTokenOnce_('my-super-secret-token');
 */
function setApiTokenOnce_(token) {
  if (!token) throw new Error('Token required');
  PropertiesService.getScriptProperties().setProperty('API_TOKEN', token);
  Logger.log('API_TOKEN set (keep this secret).');
}
