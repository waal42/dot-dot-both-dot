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
    headers = ["song", "link", "Schváleno", "Přidáno do YT"];
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

// Přidání vlastního menu při otevření tabulky
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Svatba')
    .addItem('Synchronizovat playlist 🎵', 'syncApprovedSongsToYouTube')
    .addToUi();
}

// Hlavní synchronizační logika pro YouTube playlist
function syncApprovedSongsToYouTube() {
  var sheetName = "Písničky";
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = doc.getSheetByName(sheetName);
  
  if (!sheet) {
    SpreadsheetApp.getUi().alert("Chyba: List '" + sheetName + "' neexistuje.");
    return;
  }
  
  var scriptProperties = PropertiesService.getScriptProperties();
  var playlistId = scriptProperties.getProperty('YOUTUBE_PLAYLIST_ID');
  
  if (!playlistId || playlistId.trim() === "" || playlistId.includes("YOUR_")) {
    SpreadsheetApp.getUi().alert("Chyba: V nastavení projektu (Script Properties) chybí platné 'YOUTUBE_PLAYLIST_ID'.");
    return;
  }
  
  var dataRange = sheet.getDataRange();
  var values = dataRange.getValues();
  var headers = values[0];
  
  // Nalezení indexů sloupců
  var colSong = headers.indexOf("song");
  var colLink = headers.indexOf("link");
  var colApproved = headers.indexOf("Schváleno");
  var colSynced = headers.indexOf("Přidáno do YT");
  
  if (colSong === -1 || colLink === -1 || colApproved === -1 || colSynced === -1) {
    SpreadsheetApp.getUi().alert("Chyba: Nenašel jsem všechny potřebné sloupce. Ujistěte se, že záhlaví obsahuje: 'song', 'link', 'Schváleno', 'Přidáno do YT'.");
    return;
  }
  
  var syncedCount = 0;
  var failedSongs = [];
  
  for (var i = 1; i < values.length; i++) {
    var row = values[i];
    var songName = row[colSong].toString().trim();
    var songLink = row[colLink].toString().trim();
    var isApproved = row[colApproved].toString().trim().toLowerCase() === 'ano';
    var isSynced = row[colSynced].toString().trim().toLowerCase() === 'ano';
    
    if (songName && isApproved && !isSynced) {
      var videoId = getYouTubeVideoId(songLink);
      
      // Pokud není platný odkaz, zkusíme vyhledat skladbu na YouTube podle názvu
      if (!videoId) {
        videoId = searchYouTubeVideo(songName);
      }
      
      if (videoId) {
        var success = addVideoToPlaylist(playlistId, videoId);
        if (success) {
          // Zapíšeme "Ano" do sloupce s potvrzením o synchronizaci
          sheet.getRange(i + 1, colSynced + 1).setValue("Ano");
          syncedCount++;
        } else {
          failedSongs.push(songName + " (Chyba při přidávání)");
        }
      } else {
        failedSongs.push(songName + " (Video nenalezeno)");
      }
    }
  }
  
  if (syncedCount > 0 || failedSongs.length > 0) {
    var msg = "Synchronizace dokončena.\n" +
              "✅ Úspěšně přidáno: " + syncedCount + " skladeb.\n";
    if (failedSongs.length > 0) {
      msg += "❌ Nepodařilo se přidat:\n- " + failedSongs.join("\n- ");
    }
    SpreadsheetApp.getUi().alert(msg);
  } else {
    SpreadsheetApp.getUi().toast("Žádné nové schválené skladby k synchronizaci.", "YouTube Sync");
  }
}

// Pomocná funkce na extrakci Video ID z YouTube odkazu
function getYouTubeVideoId(url) {
  if (!url) return null;
  var regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  var match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}

// Vyhledání videa na YouTube a vrácení prvního výsledku
function searchYouTubeVideo(query) {
  try {
    var results = YouTube.Search.list('id,snippet', {
      q: query,
      maxResults: 1,
      type: 'video'
    });
    if (results.items && results.items.length > 0) {
      return results.items[0].id.videoId;
    }
  } catch (e) {
    console.error("YouTube search failed for: " + query, e);
  }
  return null;
}

// Přidání videa do playlistu
function addVideoToPlaylist(playlistId, videoId) {
  try {
    YouTube.PlaylistItems.insert({
      snippet: {
        playlistId: playlistId,
        resourceId: {
          kind: 'youtube#video',
          videoId: videoId
        }
      }
    }, 'snippet');
    return true;
  } catch (e) {
    console.error("Failed to add video to playlist: " + e.message);
    return false;
  }
}
