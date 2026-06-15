#!/usr/bin/env python3
import pandas as pd
import requests
import io
import os
import re
import html

# Helper to load .env variables locally (avoiding dependency on python-dotenv)
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

# Helper for secure HTML escaping
def esc(val):
    return html.escape(str(val))

# 1. CONFIGURATION
BASE_URL = os.environ.get("PUBLIC_GOOGLE_SCRIPT_URL", "")
API_TOKEN = os.environ.get("DASHBOARD_API_TOKEN", "")

URL_HOST_CSV = f"{BASE_URL}?sheet=Hosté&token={API_TOKEN}"
URL_PISNICKY_CSV = f"{BASE_URL}?sheet=Písničky&token={API_TOKEN}"
URL_ZPRAVY_CSV = f"{BASE_URL}?sheet=Zprávy&token={API_TOKEN}"

# Target production path on the VPS
TARGET_HTML_PATH = "/var/www/mywalove/svatba/dashboard/index.html"

def download_csv(url):
    # Apps Script redirects (302), requests handles it automatically with allow_redirects=True
    response = requests.get(url, allow_redirects=True)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))

def parse_children_count(text, is_coming_with_children):
    if not is_coming_with_children or str(is_coming_with_children).lower().strip() != 'ano':
        return 0
    if pd.isna(text) or not str(text).strip():
        return 0  # Do not count empty text details to avoid double-counting across partners
    
    text_lower = str(text).lower().strip()
    
    # Check simple Czech text numbers
    if text_lower in ['jedno', '1', 'jedna', 'jeden']:
        return 1
    if text_lower in ['dve', 'dvě', '2', 'dva']:
        return 2
    if text_lower in ['tri', 'tři', '3']:
        return 3
    if text_lower in ['ctyri', 'čtyři', '4']:
        return 4
        
    # Match any explicit number followed by child-related words
    match = re.search(r'(\d+)\s*(?:dítě|dite|děti|deti|kluk|holk|syn|dcer|dět|det)', text_lower)
    if match:
        return int(match.group(1))
        
    # Match any digit in text
    digits = re.findall(r'\b\d+\b', text_lower)
    if digits:
        first_num = int(digits[0])
        if first_num <= 6:  # Reasonable count of children per family entry
            return first_num
            
    return 1  # Safe default if text has content but count cannot be parsed

def main():
    if not BASE_URL:
        print("Chyba: V konfiguraci (.env) chybí hodnota PUBLIC_GOOGLE_SCRIPT_URL.")
        return
    if not API_TOKEN:
        print("Chyba: V konfiguraci (.env) chybí hodnota DASHBOARD_API_TOKEN.")
        return
    try:
        # Load data from Google Sheets API / CSV Proxy
        df_hoste = download_csv(URL_HOST_CSV)
        df_pisnicky = download_csv(URL_PISNICKY_CSV)
        df_zpravy = download_csv(URL_ZPRAVY_CSV)
    except Exception as e:
        print(f"Chyba při stahování dat: {e}")
        return

    # Clean text columns
    df_hoste = df_hoste.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_pisnicky = df_pisnicky.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    df_zpravy = df_zpravy.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    # Helper for robust column lookup (handles casing / accents / variations)
    def find_col(df, patterns):
        for pattern in patterns:
            for col in df.columns:
                if pattern in col.lower():
                    return col
        return None

    # Resolve column names dynamically
    col_name = find_col(df_hoste, ['jméno', 'name', 'jmeno']) or df_hoste.columns[0]
    col_email = find_col(df_hoste, ['email', 'e-mail', 'mail']) or df_hoste.columns[1]
    col_rsvp = find_col(df_hoste, ['přijde?', 'rsvp', 'attendance', 'prije']) or df_hoste.columns[2]
    col_kids = find_col(df_hoste, ['děti?', 'children', 'deti']) or df_hoste.columns[3]
    col_kids_detail = find_col(df_hoste, ['kolik dětí?', 'co dělají?', 'how_many_children', 'deti_info', 'poznámka']) or df_hoste.columns[4]
    col_family = find_col(df_hoste, ['rodina?', 'family', 'rodina']) or df_hoste.columns[5]
    col_lunch = find_col(df_hoste, ['oběd?', 'lunch', 'obed']) or df_hoste.columns[6]
    col_diet = find_col(df_hoste, ['dieta', 'diet', 'alergie', 'omezení']) or df_hoste.columns[7]
    col_date = find_col(df_hoste, ['datum', 'date', 'timestamp', 'vyplně']) or df_hoste.columns[8]

    # Fill NaNs with empty string
    df_hoste = df_hoste.fillna("")

    # Filter confirmed and declined
    confirmed = df_hoste[df_hoste[col_rsvp].str.lower() == 'ano']
    declined = df_hoste[df_hoste[col_rsvp].str.lower() == 'ne']

    # Calculations for stats
    total_confirmed_adults = len(confirmed)
    total_de    # Calculate children counts (with family vs friends breakdown)
    children_list = []
    total_children = 0
    family_children = 0
    friends_children = 0
    for _, row in confirmed.iterrows():
        kids_val = row[col_kids]
        kids_detail = row[col_kids_detail]
        if str(kids_val).lower().strip() == 'ano':
            cnt = parse_children_count(kids_detail, kids_val)
            if cnt > 0:
                is_family = str(row[col_family]).lower().strip() == 'ano'
                if is_family:
                    family_children += cnt
                else:
                    friends_children += cnt
                total_children += cnt
                children_list.append({
                    "parent": esc(row[col_name]),
                    "email": esc(row[col_email]) if col_email else "Neuvedeno",
                    "count": cnt,
                    "detail": esc(kids_detail) if kids_detail else "Bez bližšího popisu",
                    "group": "Rodina" if is_family else "Kamarádi"
                })

    # Family vs Friends Breakdown (based on YES/NO in 'rodina?')
    confirmed_family = confirmed[confirmed[col_family].str.lower() == 'ano']
    confirmed_friends = confirmed[confirmed[col_family].str.lower() != 'ano']
    
    total_family = len(confirmed_family)
    total_friends = len(confirmed_friends)

    total_lunch = len(confirmed[confirmed[col_lunch].str.lower() == 'ano'])

    # Compile diets and allergies mapped to user names
    diets_list = []
    for _, row in confirmed.iterrows():
        diet_val = row[col_diet]
        if diet_val and str(diet_val).strip():
            diets_list.append({
                "name": esc(row[col_name]),
                "email": esc(row[col_email]) if col_email else "Neuvedeno",
                "diet": esc(str(diet_val).strip())
            })

    # Get recent RSVPs (latest 5 answers based on file ordering)
    activity_df = df_hoste[df_hoste[col_name].str.strip() != ""]
    recent_rsvps = []
    for _, row in activity_df.tail(5).iloc[::-1].iterrows():
        recent_rsvps.append({
            "name": esc(row[col_name]),
            "date": esc(row[col_date]) if col_date in row else "",
            "rsvp": esc(row[col_rsvp])
        })

    # Prepare songs list
    songs_col = find_col(df_pisnicky, ['song', 'písnička', 'pisnicka', 'název']) or df_pisnicky.columns[0]
    link_col = find_col(df_pisnicky, ['link', 'odkaz', 'url']) or df_pisnicky.columns[1]
    df_pisnicky = df_pisnicky.fillna("")
    songs_list = []
    for _, row in df_pisnicky.iterrows():
        song_name = row[songs_col]
        if song_name and str(song_name).strip():
            songs_list.append({
                "song": esc(song_name),
                "link": esc(row[link_col])
            })

    # Prepare messages
    msg_name_col = find_col(df_zpravy, ['jméno', 'name', 'podpis']) or df_zpravy.columns[0]
    msg_morse_col = find_col(df_zpravy, ['morse', 'morseovka']) or df_zpravy.columns[1]
    msg_decoded_col = find_col(df_zpravy, ['překlad', 'decoded', 'zpráva', 'zprava']) or df_zpravy.columns[2]
    df_zpravy = df_zpravy.fillna("")
    messages_list = []
    for _, row in df_zpravy.iterrows():
        msg_decoded = row[msg_decoded_col]
        if msg_decoded and str(msg_decoded).strip():
            messages_list.append({
                "name": esc(row[msg_name_col]) if row[msg_name_col] else "Anonym",
                "morse": esc(row[msg_morse_col]),
                "decoded": esc(msg_decoded)
            })

    # Prepare guest table rows for client side
    guests_list = []
    for _, row in df_hoste.iterrows():
        guests_list.append({
            "name": esc(row[col_name]),
            "email": esc(row[col_email]) if col_email else "Neuvedeno",
            "rsvp": esc(row[col_rsvp]),
            "lunch": esc(row[col_lunch]) if col_lunch in row else "",
            "family": esc(row[col_family]) if col_family in row else "",
            "kids": esc(row[col_kids]) if col_kids in row else "",
            "kids_detail": esc(row[col_kids_detail]) if col_kids_detail in row else "",
            "diet": esc(row[col_diet]) if col_diet in row else ""
        })

    # Generate HTML code snippets
    recent_rsvps_html = ""
    for item in recent_rsvps:
        rsvp_lower = item['rsvp'].lower()
        badge_class = 'bg-emerald-50 text-emerald-800 border border-emerald-200' if rsvp_lower == 'ano' else 'bg-rose-50 text-rose-800 border border-rose-200'
        badge_text = 'Přijde' if rsvp_lower == 'ano' else 'Nepřijde'
        recent_rsvps_html += f"""
        <div class="py-3 flex justify-between items-center text-sm">
            <div>
                <span class="font-bold text-[#2d3a2d]">{item['name']}</span>
                <span class="text-slate-400 text-xs block font-semibold">{item['date']}</span>
            </div>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold {badge_class}">
                {badge_text}
            </span>
        </div>
        """
    if not recent_rsvps_html:
        recent_rsvps_html = '<p class="text-[#7a7084]/60 text-sm py-4">Zatím žádné odpovědi.</p>'

    guest_table_html = ""
    for g in guests_list:
        rsvp_lower = g['rsvp'].lower()
        rsvp_badge_class = 'bg-emerald-50 text-emerald-800 border border-emerald-200' if rsvp_lower == 'ano' else 'bg-rose-50 text-rose-800 border border-rose-200'
        
        group_badge = '<span class="inline-block bg-[#2d3a2d] text-white px-2.5 py-0.5 rounded-sm text-xs font-bold uppercase tracking-wider">Rodina</span>' if g['family'].lower() == 'ano' else '<span class="inline-block bg-[#7a7084]/10 text-[#7a7084] px-2.5 py-0.5 rounded-sm text-xs font-bold uppercase tracking-wider">Kamarád</span>'
        
        lunch_badge = '<span class="inline-block bg-indigo-50 border border-indigo-150 text-indigo-850 px-2 py-0.5 rounded-sm text-xs font-bold">Oběd</span>' if g['lunch'].lower() == 'ano' else '<span class="text-slate-300 text-xs">-</span>'
        
        kids_info = g["kids_detail"] if g['kids'].lower() == 'ano' else '<span class="text-slate-300">-</span>'
        diet_info = g["diet"] if g['diet'] else '<span class="text-slate-300">-</span>'
        
        guest_table_html += f"""
        <tr class="guest-row" 
            data-name="{g['name'].lower()}" 
            data-email="{g['email'].lower()}" 
            data-rsvp="{g['rsvp'].upper()}" 
            data-lunch="{g['lunch'].upper()}" 
            data-kids="{g['kids'].upper()}" 
            data-family="{g['family'].upper()}"
            data-diet="{('yes' if g['diet'] else 'no')}"
            data-all-text="{g['name'].lower()} {g['email'].lower()} {g['diet'].lower()}">
            <td class="p-4 text-[#2d3a2d] font-bold">{g['name']}</td>
            <td class="p-4 text-slate-500 text-xs font-mono">{g['email']}</td>
            <td class="p-4 text-center">
                <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold {rsvp_badge_class}">
                    {g['rsvp']}
                </span>
            </td>
            <td class="p-4 text-center">
                {group_badge}
            </td>
            <td class="p-4 text-center">
                {lunch_badge}
            </td>
            <td class="p-4 text-slate-600 text-xs">
                {kids_info}
            </td>
            <td class="p-4 text-[#2d3a2d]">
                {diet_info}
            </td>
        </tr>
        """

    children_html = ""
    for item in children_list:
        group_badge_class = 'bg-[#2d3a2d] text-white' if item['group'] == 'Rodina' else 'bg-[#7a7084]/10 text-[#7a7084]'
        children_html += f"""
        <div class="p-4 rounded-sm border border-[#2d3a2d]/5 bg-[#f1f3eb]/20 flex flex-col md:flex-row md:justify-between md:items-center gap-2">
            <div>
                <span class="font-bold text-[#2d3a2d] block">{item['parent']}</span>
                <span class="text-xs text-slate-400 font-semibold block">{item['email']}</span>
                <p class="text-xs text-[#2d3a2d] mt-2 italic font-medium">"{item['detail']}"</p>
            </div>
            <div class="text-right flex flex-col items-end gap-1.5">
                <span class="inline-block bg-[#7a7084] text-white px-3 py-1 rounded-sm text-xs font-bold uppercase tracking-wider">
                    Počet dětí: {item['count']}
                </span>
                <span class="inline-block px-2 py-0.5 rounded-sm text-[9px] font-bold uppercase tracking-wider {group_badge_class}">
                    {item['group']}
                </span>
            </div>
        </div>
        """
    if not children_html:
        children_html = '<p class="text-[#7a7084]/60 text-sm text-center py-12 font-medium">Žádné děti nejsou nahlášeny.</p>'

    diets_html = ""
    for item in diets_list:
        diets_html += f"""
        <tr>
            <td class="py-4 font-bold text-[#2d3a2d] pr-4">{item['name']}</td>
            <td class="py-4 text-slate-500 pr-4 text-xs font-mono">{item['email']}</td>
            <td class="py-4 text-slate-800 leading-relaxed font-semibold">{item['diet']}</td>
        </tr>
        """
    if not diets_html:
        diets_html = '<tr><td colspan="3" class="py-6 text-[#7a7084]/60 text-center font-medium">Žádné speciální požadavky na stravu.</td></tr>'

    songs_html = ""
    for item in songs_list:
        link_html = f'<a href="{item["link"]}" target="_blank" class="mt-2 text-xs text-[#7a7084] hover:text-[#2d3a2d] hover:underline inline-flex items-center gap-1 font-semibold break-all">{item["link"]} ↗</a>' if item['link'] else '<span class="text-xs text-slate-400 italic block mt-1">Bez odkazu</span>'
        songs_html += f"""
        <div class="p-4 rounded-sm border border-[#2d3a2d]/5 bg-[#f1f3eb]/20 hover:bg-[#f1f3eb]/45 transition-all">
            <span class="font-bold text-[#2d3a2d] block text-sm">{item['song']}</span>
            {link_html}
        </div>
        """
    if not songs_html:
        songs_html = '<div class="col-span-full text-[#7a7084]/60 text-sm text-center py-12 font-medium">Zatím nebyly nahlášeny žádné písničky.</div>'

    messages_html = ""
    for item in messages_list:
        messages_html += f"""
        <div class="p-5 rounded-sm border border-[#2d3a2d]/5 bg-[#f1f3eb]/20">
            <div class="flex justify-between items-center mb-3">
                <span class="font-bold text-[#2d3a2d] text-sm">{item['name']}</span>
                <span class="text-[9px] font-bold text-[#7a7084] uppercase tracking-widest bg-white border border-[#2d3a2d]/10 px-2.5 py-0.5 rounded-sm">Vzkaz</span>
            </div>
            <p class="text-xs font-mono bg-white p-3 border border-[#2d3a2d]/5 rounded-sm mb-3 text-slate-500 overflow-x-auto whitespace-nowrap scrollbar-none italic">
                {item['morse']}
            </p>
            <p class="text-[#2d3a2d] font-semibold text-sm leading-relaxed pl-2 border-l-2 border-[#2d3a2d]">
                {item['decoded']}
            </p>
        </div>
        """
    if not messages_html:
        messages_html = '<div class="text-[#7a7084]/60 text-sm text-center py-12 font-medium">Zatím nebyly zaslány žádné vzkazy.</div>'

    # Load HTML template
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_template.html')
    if not os.path.exists(template_path):
        print(f"Chyba: Soubor šablony {template_path} neexistuje.")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Placeholders replacement
    html_content = html_content.replace("{{LAST_SYNC}}", pd.Timestamp.now().strftime('%d.%m.%Y %H:%M'))
    html_content = html_content.replace("{{TAB_GUESTS_COUNT}}", str(total_confirmed_adults))
    html_content = html_content.replace("{{TAB_CHILDREN_COUNT}}", str(total_children))
    html_content = html_content.replace("{{TAB_DIETS_COUNT}}", str(len(diets_list)))
    html_content = html_content.replace("{{TAB_SONGS_COUNT}}", str(len(songs_list)))
    html_content = html_content.replace("{{TAB_MESSAGES_COUNT}}", str(len(messages_list)))
    
    html_content = html_content.replace("{{STATS_ADULTS}}", str(total_confirmed_adults))
    html_content = html_content.replace("{{STATS_CHILDREN}}", str(total_children))
    html_content = html_content.replace("{{FAMILY_CHILDREN}}", str(family_children))
    html_content = html_content.replace("{{FRIENDS_CHILDREN}}", str(friends_children))
    html_content = html_content.replace("{{STATS_LUNCH}}", str(total_lunch))
    html_content = html_content.replace("{{STATS_DECLINED}}", str(total_declined))
    
    family_percent = (total_family / total_confirmed_adults * 100) if total_confirmed_adults > 0 else 0
    friends_percent = (total_friends / total_confirmed_adults * 100) if total_confirmed_adults > 0 else 0
    html_content = html_content.replace("{{FAMILY_COUNT}}", str(total_family))
    html_content = html_content.replace("{{FAMILY_PERCENT}}", f"{family_percent:.1f}")
    html_content = html_content.replace("{{FRIENDS_COUNT}}", str(total_friends))
    html_content = html_content.replace("{{FRIENDS_PERCENT}}", f"{friends_percent:.1f}")
    
    html_content = html_content.replace("{{RECENT_RSVPS_ROWS}}", recent_rsvps_html)
    html_content = html_content.replace("{{GUEST_TABLE_ROWS}}", guest_table_html)
    html_content = html_content.replace("{{CHILDREN_LIST_BLOCKS}}", children_html)
    html_content = html_content.replace("{{DIETS_TABLE_ROWS}}", diets_html)
    html_content = html_content.replace("{{SONGS_LIST_BLOCKS}}", songs_html)
    html_content = html_content.replace("{{MESSAGES_LIST_BLOCKS}}", messages_html)
    html_content = html_content.replace("{{FOOTER_YEAR}}", pd.Timestamp.now().strftime('%Y'))

    # Create target directory if needed and write html file
    os.makedirs(os.path.dirname(TARGET_HTML_PATH), exist_ok=True)
    with open(TARGET_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Dashboard úspěšně aktualizován.")

if __name__ == "__main__":
    main()
