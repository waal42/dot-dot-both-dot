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
BASE_URL = "https://script.google.com/macros/s/AKfycbz-gPc1HW6SuyQMTfgBU3WWw-Dg4qSwPqn9Hy5ht0xJ-Zis_H_JnN8bPrQe82bPS4YPlA/exec"
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
    total_declined = len(declined)
    
    # Calculate children counts
    children_list = []
    total_children = 0
    for _, row in confirmed.iterrows():
        kids_val = row[col_kids]
        kids_detail = row[col_kids_detail]
        if str(kids_val).lower().strip() == 'ano':
            cnt = parse_children_count(kids_detail, kids_val)
            total_children += cnt
            if cnt > 0:  # Only add to detailed UI list if there is a count > 0
                children_list.append({
                    "parent": esc(row[col_name]),
                    "email": esc(row[col_email]) if col_email else "Neuvedeno",
                    "count": cnt,
                    "detail": esc(kids_detail) if kids_detail else "Bez bližšího popisu"
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

    # HTML Generator aligned with wedding web design (Forest Pine & Sage Mist)
    html_content = f"""<!DOCTYPE html>
<html lang="cs" class="bg-[#f1f3eb] text-[#2d3a2d]">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Svatební Administrace</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Montserrat', ui-sans-serif, system-ui, sans-serif;
            background-color: #f1f3eb;
            color: #2d3a2d;
        }}
        .morse-line-dashboard {{
            background-image: repeating-linear-gradient(
                to right,
                currentColor,
                currentColor 4px,
                transparent 4px,
                transparent 8px,
                currentColor 8px,
                currentColor 20px,
                transparent 20px,
                transparent 24px
            );
        }}
    </style>
</head>
<body class="p-4 md:p-8 max-w-7xl mx-auto min-h-screen flex flex-col">

    <!-- Header -->
    <header class="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b border-[#2d3a2d]/10 pb-6 gap-4">
        <div>
            <h1 class="text-3xl font-extrabold text-[#2d3a2d] tracking-wider uppercase flex items-center gap-3">
                Svatební Dashboard
            </h1>
            <div class="morse-line-dashboard h-[2px] w-32 mt-2 text-[#7a7084]"></div>
        </div>
        <div class="text-left md:text-right bg-white border border-[#2d3a2d]/10 rounded-sm p-3 text-xs text-[#2d3a2d] font-bold shadow-xs">
            Poslední synchronizace: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}
        </div>
    </header>

    <!-- Navigation Tabs -->
    <nav class="flex border-b border-[#2d3a2d]/10 mb-8 overflow-x-auto whitespace-nowrap scrollbar-none gap-2">
        <button onclick="switchTab('tab-overview')" id="btn-tab-overview" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-[#2d3a2d] text-[#2d3a2d] transition-all cursor-pointer">
            📊 Přehled
        </button>
        <button onclick="switchTab('tab-guests')" id="btn-tab-guests" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-transparent text-[#7a7084] hover:text-[#2d3a2d] transition-all cursor-pointer">
            👥 Hosté ({total_confirmed_adults})
        </button>
        <button onclick="switchTab('tab-kids')" id="btn-tab-kids" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-transparent text-[#7a7084] hover:text-[#2d3a2d] transition-all cursor-pointer">
            🧸 Děti ({total_children})
        </button>
        <button onclick="switchTab('tab-diets')" id="btn-tab-diets" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-transparent text-[#7a7084] hover:text-[#2d3a2d] transition-all cursor-pointer">
            🍽️ Diety ({len(diets_list)})
        </button>
        <button onclick="switchTab('tab-songs')" id="btn-tab-songs" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-transparent text-[#7a7084] hover:text-[#2d3a2d] transition-all cursor-pointer">
            🎵 Písničky ({len(songs_list)})
        </button>
        <button onclick="switchTab('tab-messages')" id="btn-tab-messages" class="tab-btn py-3 px-6 text-xs font-bold uppercase tracking-widest border-b-2 border-transparent text-[#7a7084] hover:text-[#2d3a2d] transition-all cursor-pointer">
            ✉️ Vzkazy ({len(messages_list)})
        </button>
    </nav>

    <!-- Content Sections -->
    <main class="flex-grow">

        <!-- 1. OVERVIEW TAB -->
        <section id="tab-overview" class="tab-content space-y-8 block">
            <!-- Stats Grid -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
                <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10 flex flex-col justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-[#7a7084]">Potvrzení Dospělí</span>
                    <span class="text-4xl font-black text-[#2d3a2d] mt-2">{total_confirmed_adults}</span>
                </div>
                <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10 flex flex-col justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-[#7a7084]">Celkem Děti</span>
                    <span class="text-4xl font-black text-[#7a7084] mt-2">{total_children}</span>
                </div>
                <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10 flex flex-col justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-[#7a7084]">Hosté na Oběd</span>
                    <span class="text-4xl font-black text-[#2d3a2d] mt-2">{total_lunch}</span>
                </div>
                <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10 flex flex-col justify-between">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-[#7a7084]">Omluvení (RSVP Ne)</span>
                    <span class="text-4xl font-black text-rose-700 mt-2">{total_declined}</span>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Left Column (Categories & Recent Activity) -->
                <div class="lg:col-span-2 space-y-8">
                    <!-- Family Breakdown -->
                    <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">👨‍👩‍👧‍👦 Kategorie hostů</h2>
                        <div class="space-y-5">
                            <div>
                                <div class="flex justify-between text-xs font-bold uppercase mb-1">
                                    <span class="text-[#7a7084]">Rodina (Zvaní k obědu)</span>
                                    <span class="text-[#2d3a2d]">{total_family} hostů</span>
                                </div>
                                <div class="w-full bg-[#f1f3eb] rounded-sm h-3">
                                    <div class="bg-[#2d3a2d] h-3 rounded-sm" style="width: {(total_family / total_confirmed_adults * 100) if total_confirmed_adults > 0 else 0}%"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-xs font-bold uppercase mb-1">
                                    <span class="text-[#7a7084]">Kamarádi (Zvaní na večerní oslavu)</span>
                                    <span class="text-[#2d3a2d]">{total_friends} hostů</span>
                                </div>
                                <div class="w-full bg-[#f1f3eb] rounded-sm h-3">
                                    <div class="bg-[#7a7084] h-3 rounded-sm" style="width: {(total_friends / total_confirmed_adults * 100) if total_confirmed_adults > 0 else 0}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">⏱️ Nejnovější odpovědi</h2>
                        <div class="divide-y divide-[#2d3a2d]/5">
                            {"".join([f'''
                            <div class="py-3 flex justify-between items-center text-sm">
                                <div>
                                    <span class="font-bold text-[#2d3a2d]">{item['name']}</span>
                                    <span class="text-slate-400 text-xs block font-semibold">{item['date']}</span>
                                </div>
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold { 'bg-emerald-50 text-emerald-800 border border-emerald-200' if item['rsvp'].lower() == 'ano' else 'bg-rose-50 text-rose-800 border border-rose-200' }">
                                    { 'Přijde' if item['rsvp'].lower() == 'ano' else 'Nepřijde' }
                                </span>
                            </div>
                            ''' for item in recent_rsvps]) if recent_rsvps else '<p class="text-[#7a7084]/60 text-sm py-4">Zatím žádné odpovědi.</p>'}
                        </div>
                    </div>
                </div>

                <!-- Right Column (Quick Contacts & Overview Guide) -->
                <div class="space-y-8">
                    <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                        <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-4">💡 Rychlý tip</h2>
                        <p class="text-xs text-[#7a7084] leading-relaxed font-semibold">
                            Chcete vyhledat konkrétní diety, bezlepkové stravování nebo vegetariány? Přejděte na novou záložku <strong>Diety</strong> nebo využijte vyhledávač v záložce <strong>Hosté</strong>.
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <!-- 2. GUESTS TAB -->
        <section id="tab-guests" class="tab-content space-y-6 hidden">
            <!-- Search & Filters Bar -->
            <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10 flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
                <div class="flex-grow max-w-md">
                    <input type="text" id="guest-search" oninput="filterGuestsTable()" placeholder="Vyhledat hosta podle jména, e-mailu..." 
                           class="w-full px-4 py-2.5 rounded-sm border border-[#2d3a2d]/10 text-sm focus:outline-none focus:ring-1 focus:ring-[#2d3a2d] font-medium bg-[#f1f3eb]/20">
                </div>
                <div class="flex flex-wrap gap-2">
                    <select id="filter-rsvp" onchange="filterGuestsTable()" class="px-3 py-2 rounded-sm border border-[#2d3a2d]/10 text-xs font-bold bg-white text-[#2d3a2d] focus:outline-none focus:ring-1 focus:ring-[#2d3a2d]">
                        <option value="ALL">Všechny RSVP</option>
                        <option value="ANO">RSVP: Přijde</option>
                        <option value="NE">RSVP: Nepřijde</option>
                    </select>
                    <select id="filter-family" onchange="filterGuestsTable()" class="px-3 py-2 rounded-sm border border-[#2d3a2d]/10 text-xs font-bold bg-white text-[#2d3a2d] focus:outline-none focus:ring-1 focus:ring-[#2d3a2d]">
                        <option value="ALL">Všichni hosté</option>
                        <option value="ANO">Pouze Rodina</option>
                        <option value="NE">Pouze Kamarádi</option>
                    </select>
                    <select id="filter-lunch" onchange="filterGuestsTable()" class="px-3 py-2 rounded-sm border border-[#2d3a2d]/10 text-xs font-bold bg-white text-[#2d3a2d] focus:outline-none focus:ring-1 focus:ring-[#2d3a2d]">
                        <option value="ALL">Všechny obědy</option>
                        <option value="ANO">Na oběd: Ano</option>
                        <option value="NE">Na oběd: Ne</option>
                    </select>
                    <select id="filter-kids" onchange="filterGuestsTable()" class="px-3 py-2 rounded-sm border border-[#2d3a2d]/10 text-xs font-bold bg-white text-[#2d3a2d] focus:outline-none focus:ring-1 focus:ring-[#2d3a2d]">
                        <option value="ALL">Děti: Vše</option>
                        <option value="ANO">Pouze S dětmi</option>
                        <option value="NE">Pouze Bez dětí</option>
                    </select>
                    <select id="filter-diet" onchange="filterGuestsTable()" class="px-3 py-2 rounded-sm border border-[#2d3a2d]/10 text-xs font-bold bg-white text-[#2d3a2d] focus:outline-none focus:ring-1 focus:ring-[#2d3a2d]">
                        <option value="ALL">Diety: Vše</option>
                        <option value="DIET">Pouze S dietou</option>
                        <option value="NODIET">Pouze Bez diety</option>
                    </select>
                </div>
            </div>

            <!-- Table Card -->
            <div class="bg-white rounded-sm shadow-xs border border-[#2d3a2d]/10 overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm" id="guests-table-el">
                        <thead>
                            <tr class="bg-[#f1f3eb]/45 border-b border-[#2d3a2d]/10 text-[#7a7084] font-bold text-xs uppercase">
                                <th class="p-4">Jméno</th>
                                <th class="p-4">E-mail</th>
                                <th class="p-4 text-center">RSVP</th>
                                <th class="p-4 text-center">Skupina</th>
                                <th class="p-4 text-center">Oběd</th>
                                <th class="p-4">Děti</th>
                                <th class="p-4">Dieta</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-[#2d3a2d]/5 font-medium">
                            {"".join([f'''
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
                                    <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold { 'bg-emerald-50 text-emerald-800 border border-emerald-200' if g['rsvp'].lower() == 'ano' else 'bg-rose-50 text-rose-800 border border-rose-200' }">
                                        {g['rsvp']}
                                    </span>
                                </td>
                                <td class="p-4 text-center">
                                    { f'<span class="inline-block bg-[#2d3a2d] text-white px-2.5 py-0.5 rounded-sm text-xs font-bold uppercase tracking-wider">Rodina</span>' if g['family'].lower() == 'ano' else '<span class="inline-block bg-[#7a7084]/10 text-[#7a7084] px-2.5 py-0.5 rounded-sm text-xs font-bold uppercase tracking-wider">Kamarád</span>' }
                                </td>
                                <td class="p-4 text-center">
                                    { f'<span class="inline-block bg-indigo-50 border border-indigo-150 text-indigo-850 px-2 py-0.5 rounded-sm text-xs font-bold">Oběd</span>' if g['lunch'].lower() == 'ano' else '<span class="text-slate-300 text-xs">-</span>' }
                                </td>
                                <td class="p-4 text-slate-600 text-xs">
                                    { g["kids_detail"] if g['kids'].lower() == 'ano' else '<span class="text-slate-300">-</span>' }
                                </td>
                                <td class="p-4 text-[#2d3a2d]">
                                    { g["diet"] if g['diet'] else '<span class="text-slate-300">-</span>' }
                                </td>
                            </tr>
                            ''' for g in guests_list])}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 3. CHILDREN TAB -->
        <section id="tab-kids" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">🧸 Přehled nahlášených dětí ({total_children})</h2>
                <div class="space-y-4 max-w-3xl">
                    {"".join([f'''
                    <div class="p-4 rounded-sm border border-[#2d3a2d]/5 bg-[#f1f3eb]/20 flex flex-col md:flex-row md:justify-between md:items-center gap-2">
                        <div>
                            <span class="font-bold text-[#2d3a2d] block">{item['parent']}</span>
                            <span class="text-xs text-slate-400 font-semibold block">{item['email']}</span>
                            <p class="text-xs text-[#2d3a2d] mt-2 italic font-medium">"{item['detail']}"</p>
                        </div>
                        <div class="text-right">
                            <span class="inline-block bg-[#7a7084] text-white px-3 py-1 rounded-sm text-xs font-bold uppercase tracking-wider">
                                Počet dětí: {item['count']}
                            </span>
                        </div>
                    </div>
                    ''' for item in children_list]) if children_list else '<p class="text-[#7a7084]/60 text-sm text-center py-12 font-medium">Žádné děti nejsou nahlášeny.</p>'}
                </div>
            </div>
        </section>

        <!-- 4. DIETS TAB -->
        <section id="tab-diets" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">🍽️ Alergie a speciální stravování</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm border-collapse">
                        <thead>
                            <tr class="border-b border-[#2d3a2d]/10 text-[#7a7084] font-bold text-xs uppercase">
                                <th class="pb-3 pr-4">Host</th>
                                <th class="pb-3 pr-4">E-mail</th>
                                <th class="pb-3">Omezení / Alergie</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-[#2d3a2d]/5">
                            {"".join([f'''
                            <tr>
                                <td class="py-4 font-bold text-[#2d3a2d] pr-4">{item['name']}</td>
                                <td class="py-4 text-slate-500 pr-4 text-xs font-mono">{item['email']}</td>
                                <td class="py-4 text-slate-800 leading-relaxed font-semibold">{item['diet']}</td>
                            </tr>
                            ''' for item in diets_list]) if diets_list else '<tr><td colspan="3" class="py-6 text-[#7a7084]/60 text-center font-medium">Žádné speciální požadavky na stravu.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 5. SONGS TAB -->
        <section id="tab-songs" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">🎵 Písničky na přání</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {"".join([f'''
                    <div class="p-4 rounded-sm border border-[#2d3a2d]/5 bg-[#f1f3eb]/20 hover:bg-[#f1f3eb]/45 transition-all">
                        <span class="font-bold text-[#2d3a2d] block text-sm">{item['song']}</span>
                        {f'<a href="{item["link"]}" target="_blank" class="mt-2 text-xs text-[#7a7084] hover:text-[#2d3a2d] hover:underline inline-flex items-center gap-1 font-semibold break-all">{item["link"]} ↗</a>' if item['link'] else '<span class="text-xs text-slate-400 italic block mt-1">Bez odkazu</span>'}
                    </div>
                    ''' for item in songs_list]) if songs_list else '<div class="col-span-full text-[#7a7084]/60 text-sm text-center py-12 font-medium">Zatím nebyly nahlášeny žádné písničky.</div>'}
                </div>
            </div>
        </section>

        <!-- 6. MESSAGES TAB -->
        <section id="tab-messages" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-sm shadow-xs border border-[#2d3a2d]/10">
                <h2 class="text-sm font-bold uppercase tracking-widest text-[#2d3a2d] mb-6 flex items-center gap-2">✉️ Vzkazy v morseovce</h2>
                <div class="space-y-4 max-w-3xl">
                    {"".join([f'''
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
                    ''' for item in messages_list]) if messages_list else '<div class="text-[#7a7084]/60 text-sm text-center py-12 font-medium">Zatím nebyly zaslány žádné vzkazy.</div>'}
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-6 border-t border-[#2d3a2d]/10 text-center text-[10px] font-bold uppercase tracking-widest text-[#7a7084]">
        Wedding Admin Dashboard &copy; {pd.Timestamp.now().strftime('%Y')}
    </footer>

    <!-- Interactive Client-Side logic -->
    <script>
        function switchTab(tabId) {{
            // Hide all sections
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.add('hidden');
                tab.classList.remove('block');
            }});
            // Show target section
            const target = document.getElementById(tabId);
            target.classList.remove('hidden');
            target.classList.add('block');

            // Reset navigation tab indicators
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('border-[#2d3a2d]', 'text-[#2d3a2d]');
                btn.classList.add('border-transparent', 'text-[#7a7084]');
            }});
            
            // Activate selected tab button indicator
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.classList.remove('border-transparent', 'text-[#7a7084]');
            activeBtn.classList.add('border-[#2d3a2d]', 'text-[#2d3a2d]');
        }}

        function filterGuestsTable() {{
            const searchQuery = document.getElementById('guest-search').value.toLowerCase().trim();
            const rsvpFilter = document.getElementById('filter-rsvp').value;
            const familyFilter = document.getElementById('filter-family').value;
            const lunchFilter = document.getElementById('filter-lunch').value;
            const kidsFilter = document.getElementById('filter-kids').value;
            const dietFilter = document.getElementById('filter-diet').value;

            document.querySelectorAll('.guest-row').forEach(row => {{
                const allText = row.getAttribute('data-all-text') || '';
                const rsvp = row.getAttribute('data-rsvp') || '';
                const lunch = row.getAttribute('data-lunch') || '';
                const kids = row.getAttribute('data-kids') || '';
                const family = row.getAttribute('data-family') || '';
                const diet = row.getAttribute('data-diet') || '';

                // Search query match
                const matchSearch = searchQuery === '' || allText.includes(searchQuery);

                // Filters match
                const matchRsvp = rsvpFilter === 'ALL' || rsvp === rsvpFilter;
                const matchFamily = familyFilter === 'ALL' || family === familyFilter;
                const matchLunch = lunchFilter === 'ALL' || lunch === lunchFilter;
                
                // Kids filter (All, Yes, No)
                const matchKids = kidsFilter === 'ALL' || (kidsFilter === 'ANO' && kids === 'ANO') || (kidsFilter === 'NE' && kids !== 'ANO');
                
                // Diet filter (All, Yes, No)
                const matchDiet = dietFilter === 'ALL' || (dietFilter === 'DIET' && diet === 'yes') || (dietFilter === 'NODIET' && diet !== 'yes');

                if (matchSearch && matchRsvp && matchFamily && matchLunch && matchKids && matchDiet) {{
                    row.classList.remove('hidden');
                }} else {{
                    row.classList.add('hidden');
                }}
            }});
        }}
    </script>

</body>
</html>
"""
    # Create target directory if needed and write html file
    os.makedirs(os.path.dirname(TARGET_HTML_PATH), exist_ok=True)
    with open(TARGET_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Dashboard úspěšně aktualizován.")

if __name__ == "__main__":
    main()
