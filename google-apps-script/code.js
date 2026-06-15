// Google Apps Script code to handle RSVP, Song suggestions, and Guestbook Morse messages
// Configure properties 'RSVP_WEBHOOK_URL', 'MESSAGE_WEBHOOK_URL', 'DASHBOARD_API_TOKEN'
// in your Apps Script project settings (Project Settings -> Script Properties).

function doPost(e) {
  var data = e.parameter;
  
  // Ochrana proti spamu (Honeypot)
  if (data.website_hp && data.website_hp.toString().trim() !== "") {
    console.warn("Spam detected and blocked: website_hp was filled.");
    return ContentService.createTextOutput(JSON.stringify({ "result": "success", "info": "spam_blocked" }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var formType = data.form_type;
  var sheetName = "Hosté"; 
  var headers = [];

  // Mapování podle tvých reálných CSV struktur v Google Sheets
  if (formType === "message") {
    sheetName = "Zprávy";
    headers = ["Jméno / Podpis", "Morseovka", "Překlad"];
  } else if (formType === "song") {
    sheetName = "Písničky";
    headers = ["song", "link"];
  } else {
    sheetName = "Hosté";
    headers = [
      "jméno",
      "e-mail",
      "přijde?",
      "děti?",
      "kolik dětí? a co dělají?",
      "rodina?",
      "přijde na oběd?",
      "dieta"
    ];
  }

  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = doc.getSheetByName(sheetName);
  
  if (!sheet) {
    sheet = doc.insertSheet(sheetName);
    var timestampName = (formType === "message") ? "Datum" : ((formType === "song") ? "Timestamp" : "datum vyplnění");
    sheet.appendRow([timestampName].concat(headers));
  }

  // Sestavení řádku
  var row = [new Date()];
  for (var i = 0; i < headers.length; i++) {
    row.push(data[headers[i]] || "");
  }

  sheet.appendRow(row);

  // --- DISCORD NOTIFICATIONS ---
  try {
    var scriptProperties = PropertiesService.getScriptProperties();
    var MESSAGE_WEBHOOK_URL = scriptProperties.getProperty('MESSAGE_WEBHOOK_URL');
    var RSVP_WEBHOOK_URL = scriptProperties.getProperty('RSVP_WEBHOOK_URL');

    if (formType === "message") {
      var discordMsg = "✉️ **Nová zpráva!**\n";
      discordMsg += `> **Od:** ${data["Jméno / Podpis"] || data["name"] || "Anonymous"}\n`;
      discordMsg += `> **Text:** ${data["Překlad"] || data["decoded_message"] || data["Morseovka"] || ""}\n`;
      
      sendToDiscord(MESSAGE_WEBHOOK_URL, discordMsg);
      
    } else if (formType !== "song") {
      var discordMsg = "🎉 **Nové vyplnění RSVP formuláře!**\n";
      for (var j = 0; j < headers.length; j++) {
        var val = data[headers[j]];
        if (val && val.toString().trim() !== "") {
          discordMsg += `> **${headers[j]}:** ${val}\n`;
        }
      }
      
      sendToDiscord(RSVP_WEBHOOK_URL, discordMsg);
    }
  } catch (err) {
    console.error("Discord Notification Failed: ", err);
  }

  return ContentService.createTextOutput(JSON.stringify({ "result": "success" }))
    .setMimeType(ContentService.MimeType.JSON);
}

// Pomocná funkce pro odeslání na Discord
function sendToDiscord(url, message) {
  if (!url || url.includes("YOUR_") || url.trim() === "") return; 
  
  var options = {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify({ content: message }),
    muteHttpExceptions: true
  };
  
  var response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() === 429) {
    console.warn("Discord nás odmítl kvůli Rate Limitu (429). Zpráva nebyla doručena: " + message);
  }
}

// GET endpoint pro Python dashboard (Zabezpečený pomocí tokenu)
function doGet(e) {
  var token = e.parameter.token;
  var expectedToken = PropertiesService.getScriptProperties().getProperty('DASHBOARD_API_TOKEN');
  
  if (!expectedToken || token !== expectedToken) {
    return ContentService.createTextOutput("Chyba: Nepovolený přístup (Unauthorized). Zkontrolujte konfiguraci tokenu.")
      .setMimeType(ContentService.MimeType.TEXT);
  }

  var sheetName = e.parameter.sheet; 
  
  if (!sheetName) {
    return ContentService.createTextOutput("Chybí parametr 'sheet'. Použij např. ?sheet=Hosté")
      .setMimeType(ContentService.MimeType.TEXT);
  }
  
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = doc.getSheetByName(sheetName);
  
  if (!sheet) {
    return ContentService.createTextOutput("List s názvem '" + sheetName + "' neexistuje.")
      .setMimeType(ContentService.MimeType.TEXT);
  }
  
  var data = sheet.getDataRange().getValues();
  var csvContent = "";
  
  for (var r = 0; r < data.length; r++) {
    var row = data[r];
    for (var c = 0; c < row.length; c++) {
      var cell = row[c];
      
      if (cell instanceof Date) {
        cell = Utilities.formatDate(cell, doc.getSpreadsheetTimeZone(), "d.M.yyyy H:mm:ss");
      } else {
        cell = cell.toString();
      }
      
      if (cell.indexOf(",") !== -1 || cell.indexOf("\n") !== -1 || cell.indexOf('"') !== -1) {
        cell = '"' + cell.replace(/"/g, '""') + '"';
      }
      
      row[c] = cell;
    }
    csvContent += row.join(",") + "\r\n";
  }
  
  return ContentService.createTextOutput(csvContent)
    .setMimeType(ContentService.MimeType.TEXT);
}

// Ostrá testovací funkce pro schválení oprávnění v Google
function test() { 
  var scriptProperties = PropertiesService.getScriptProperties();
  var MESSAGE_WEBHOOK_URL = scriptProperties.getProperty('MESSAGE_WEBHOOK_URL');
  sendToDiscord(MESSAGE_WEBHOOK_URL, "Status check: Propojení Apps Script -> Discord funguje! ✅"); 
}
