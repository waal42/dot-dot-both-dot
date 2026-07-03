# ⚙️ Google Apps Script Konfigurace

Tato složka obsahuje bezpečný a ořezaný kód pro Google Apps Script, který neobsahuje žádné tajné webhooky ani tokeny. Ty jsou uloženy v interním nastavení projektu (*Script Properties*).

## 🚀 Postup nasazení a konfigurace

1. **Otevřete Google Apps Script Editor:**
   - Jděte do své Google Tabulky (se svatebními daty).
   - V menu klikněte na **Rozšíření (Extensions)** -> **Apps Script**.

2. **Zkopírujte kód:**
   - Otevřete soubor [code.js](code.js) v tomto repozitáři.
   - Zkopírujte celý jeho obsah a vložte jej do editoru v Google Apps Scriptu (nahraďte původní kód v souboru `Kód.gs` nebo `Code.gs`).
   - Uložte projekt (kliknutím na ikonu diskety nebo zkratkou `Ctrl + S`).

3. **Nastavte Vlastnosti projektu (Script Properties):**
   - V levém panelu editoru klikněte na ikonu ozubeného kolečka **Nastavení projektu (Project Settings)**.
   - Sjeďte dolů na sekci **Vlastnosti skriptu (Script Properties)**.
   - Klikněte na **Přidat vlastnost skriptu (Add script property)** a přidejte následující 3 klíče a jejich hodnoty:
     
     * **`RSVP_WEBHOOK_URL`**: Vložte URL adresu vašeho Discord webhooku pro oznámení o RSVP.
     * **`MESSAGE_WEBHOOK_URL`**: Vložte URL adresu vašeho Discord webhooku pro vzkazy v morseovce.
     * **`DASHBOARD_API_TOKEN`**: Vložte stejný tajný token, který máte nakonfigurovaný ve vašem `.env` souboru na VPS jako `DASHBOARD_API_TOKEN` (např. dlouhý náhodný řetězec).
     
   - Klikněte na **Uložit vlastnosti skriptu (Save script properties)**.

4. **Nasaďte skript jako Webovou aplikaci (Web App):**
   - Klikněte vpravo nahoře na **Nasadit (Deploy)** -> **Nové nasazení (New deployment)**.
   - Vyberte typ **Webová aplikace (Web app)**.
   - Nastavte:
     * **Spustit jako (Execute as):** Já (vaše e-mailová adresa).
     * **Kdo má přístup (Who has access):** Kdokoliv (Anyone) – *to je nutné, aby lidé z webu mohli posílat formuláře*.
   - Klikněte na **Nasadit (Deploy)**.
   - Pokud se objeví výzva k udělení oprávnění (Authorize Access), potvrďte ji a schvalte přístup k tabulkám a externím službám (Discord).
   - Zkopírujte **URL adresu webové aplikace (Web app URL)**. Tato URL musí odpovídat hodnotě `PUBLIC_GOOGLE_SCRIPT_URL` ve vašem `.env` souboru.

5. **Povolení YouTube Playlist Synchronizace (Nepovinné):**
   Pokud chcete využít automatickou synchronizaci schválených písniček z tabulky do YouTube playlistu:
   - V levém panelu editoru klikněte na tlačítko **+** vedle položky **Služby (Services)**.
   - Vyhledejte a vyberte **YouTube Data API v3** a klikněte na **Přidat (Add)**.
   - Jděte do **Nastavení projektu (Project Settings)** -> **Vlastnosti skriptu (Script Properties)**.
   - Klikněte na **Přidat vlastnost skriptu (Add script property)** a přidejte klíč:
     * **`YOUTUBE_PLAYLIST_ID`**: ID vašeho YouTube playlistu (např. část URL za `list=`, např. `PL12345XYZ...`).
   - Uložte vlastnosti skriptu.
   - **Tip:** Po obnovení tabulky (Google Sheet) se vám v horním menu zobrazí položka **Svatba** -> **Synchronizovat playlist 🎵**.
   - První spuštění vyvolá standardní Google dialog pro udělení oprávnění k přístupu k vašemu YouTube účtu.
