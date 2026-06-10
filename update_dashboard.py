#!/usr/bin/env python3
import pandas as pd
import requests
import io
import os
import re

# 1. CONFIGURATION
BASE_URL = "https://script.google.com/macros/s/AKfycbz-gPc1HW6SuyQMTfgBU3WWw-Dg4qSwPqn9Hy5ht0xJ-Zis_H_JnN8bPrQe82bPS4YPlA/exec"

URL_HOST_CSV = f"{BASE_URL}?sheet=Hosté"
URL_PISNICKY_CSV = f"{BASE_URL}?sheet=Písničky"
URL_ZPRAVY_CSV = f"{BASE_URL}?sheet=Zprávy"

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
        return 1  # Fallback to 1 if checked but empty
    
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
            
    return 1  # Safe default if "ano" but count cannot be parsed

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
    col_lunch = find_col(df_hoste, ['oběd?', 'lunch', 'obed']) or df_hoste.columns[5]
    col_diet = find_col(df_hoste, ['dieta', 'diet', 'alergie', 'omezení']) or df_hoste.columns[6]
    col_family = find_col(df_hoste, ['rodina?', 'family', 'skupina', 'strana']) or df_hoste.columns[7]

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
            children_list.append({
                "parent": row[col_name],
                "count": cnt,
                "detail": kids_detail if kids_detail else "Bez bližšího popisu"
            })

    total_lunch = len(confirmed[confirmed[col_lunch].str.lower() == 'ano'])

    # Compile family counts
    family_counts = confirmed[col_family].value_counts().to_dict() if col_family in confirmed.columns else {}

    # Compile diets and allergies mapped to user names
    diets_list = []
    for _, row in confirmed.iterrows():
        diet_val = row[col_diet]
        if diet_val and str(diet_val).strip():
            diets_list.append({
                "name": row[col_name],
                "email": row[col_email] if col_email else "Neuvedeno",
                "diet": str(diet_val).strip()
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
                "song": song_name,
                "link": row[link_col]
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
                "name": row[msg_name_col] if row[msg_name_col] else "Anonym",
                "morse": row[msg_morse_col],
                "decoded": msg_decoded
            })

    # Prepare guest table rows for client side
    guests_list = []
    for _, row in df_hoste.iterrows():
        guests_list.append({
            "name": row[col_name],
            "email": row[col_email] if col_email else "Neuvedeno",
            "rsvp": row[col_rsvp],
            "lunch": row[col_lunch] if col_lunch in row else "",
            "family": row[col_family] if col_family in row else "Ostatní",
            "kids": row[col_kids] if col_kids in row else "",
            "kids_detail": row[col_kids_detail] if col_kids_detail in row else "",
            "diet": row[col_diet] if col_diet in row else ""
        })

    # HTML Generator
    html_content = f"""<!DOCTYPE html>
<html lang="cs" class="bg-slate-50 text-slate-800">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Svatební Administrace</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
        }}
    </style>
</head>
<body class="p-4 md:p-8 max-w-7xl mx-auto min-h-screen flex flex-col">

    <!-- Header -->
    <header class="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-200 pb-6 gap-4">
        <div>
            <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
                Svatební Dashboard <span class="text-2xl animate-pulse">💍</span>
            </h1>
            <p class="text-sm text-slate-500 font-medium">Správa a přehled odpovědí pro svatební hosty</p>
        </div>
        <div class="text-left md:text-right bg-indigo-50 border border-indigo-100 rounded-lg p-3 text-xs text-indigo-700 font-semibold shadow-xs">
            Poslední synchronizace: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}
        </div>
    </header>

    <!-- Navigation Tabs -->
    <nav class="flex border-b border-slate-200 mb-8 overflow-x-auto whitespace-nowrap scrollbar-none gap-2">
        <button onclick="switchTab('tab-overview')" id="btn-tab-overview" class="tab-btn py-3 px-6 text-sm font-semibold border-b-2 border-indigo-600 text-indigo-600 transition-all cursor-pointer">
            📊 Přehled
        </button>
        <button onclick="switchTab('tab-guests')" id="btn-tab-guests" class="tab-btn py-3 px-6 text-sm font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-900 transition-all cursor-pointer">
            👥 Hosté ({total_confirmed_adults})
        </button>
        <button onclick="switchTab('tab-songs')" id="btn-tab-songs" class="tab-btn py-3 px-6 text-sm font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-900 transition-all cursor-pointer">
            🎵 Písničky ({len(songs_list)})
        </button>
        <button onclick="switchTab('tab-messages')" id="btn-tab-messages" class="tab-btn py-3 px-6 text-sm font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-900 transition-all cursor-pointer">
            ✉️ Vzkazy ({len(messages_list)})
        </button>
    </nav>

    <!-- Content Sections -->
    <main class="flex-grow">

        <!-- 1. OVERVIEW TAB -->
        <section id="tab-overview" class="tab-content space-y-8 block">
            <!-- Stats Grid -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
                <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 flex flex-col justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Potvrzení Dospělí</span>
                    <span class="text-4xl font-extrabold text-emerald-600 mt-2">{total_confirmed_adults}</span>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 flex flex-col justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Celkem Děti</span>
                    <span class="text-4xl font-extrabold text-amber-500 mt-2">{total_children}</span>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 flex flex-col justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Hosté na Oběd</span>
                    <span class="text-4xl font-extrabold text-indigo-600 mt-2">{total_lunch}</span>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 flex flex-col justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-400">Omluvení (RSVP Ne)</span>
                    <span class="text-4xl font-extrabold text-rose-500 mt-2">{total_declined}</span>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Left Column (Families & Diets) -->
                <div class="lg:col-span-2 space-y-8">
                    <!-- Family Breakdown -->
                    <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
                        <h2 class="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">👨‍👩‍👧‍👦 Složení a rodiny</h2>
                        <div class="space-y-4">
                            {"".join([f'''
                            <div>
                                <div class="flex justify-between text-sm font-semibold mb-1">
                                    <span class="text-slate-600">{k if str(k) != 'nan' and str(k) != '' else 'Nezařazeno'}</span>
                                    <span class="text-slate-900">{v} hostů</span>
                                </div>
                                <div class="w-full bg-slate-100 rounded-full h-2.5">
                                    <div class="bg-indigo-600 h-2.5 rounded-full" style="width: {(v / total_confirmed_adults * 100) if total_confirmed_adults > 0 else 0}%"></div>
                                </div>
                            </div>
                            ''' for k, v in family_counts.items()]) if family_counts else '<p class="text-slate-400 text-sm">Žádné skupiny nebyly zavedeny.</p>'}
                        </div>
                    </div>

                    <!-- Diets Mapped to Names -->
                    <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
                        <h2 class="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">🍽️ Alergie a speciální stravování</h2>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-sm border-collapse">
                                <thead>
                                    <tr class="border-b border-slate-200 text-slate-400 font-bold text-xs uppercase">
                                        <th class="pb-3 pr-4">Host</th>
                                        <th class="pb-3 pr-4">E-mail</th>
                                        <th class="pb-3">Omezení / Alergie</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    {"".join([f'''
                                    <tr>
                                        <td class="py-3 font-semibold text-slate-900 pr-4">{item['name']}</td>
                                        <td class="py-3 text-slate-500 pr-4 text-xs font-mono">{item['email']}</td>
                                        <td class="py-3"><span class="inline-block bg-rose-50 text-rose-700 font-semibold text-xs px-2.5 py-1 rounded-md border border-rose-100">{item['diet']}</span></td>
                                    </tr>
                                    ''' for item in diets_list]) if diets_list else '<tr><td colspan="3" class="py-6 text-slate-400 text-center font-medium">Žádné speciální požadavky na dietu.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Right Column (Kids Details) -->
                <div class="space-y-8">
                    <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
                        <h2 class="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">🧸 Poznámky k dětem</h2>
                        <div class="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                            {"".join([f'''
                            <div class="border-l-4 border-amber-400 pl-4 py-2 bg-amber-50/30 rounded-r-xl pr-2 border border-l-amber-400 border-slate-100">
                                <span class="font-bold text-slate-900 block text-sm">{item['parent']}</span>
                                <span class="text-xs font-bold text-amber-700 block mb-1">Počet dětí: {item['count']}</span>
                                <p class="text-xs text-slate-600 leading-relaxed font-medium italic">"{item['detail']}"</p>
                            </div>
                            ''' for item in children_list]) if children_list else '<p class="text-slate-400 text-sm text-center py-6 font-medium">Žádné děti nejsou nahlášeny.</p>'}
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 2. GUESTS TAB -->
        <section id="tab-guests" class="tab-content space-y-6 hidden">
            <!-- Search & Filters Bar -->
            <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100 flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
                <div class="flex-grow max-w-md">
                    <input type="text" id="guest-search" oninput="filterGuestsTable()" placeholder="Vyhledat hosta podle jména, e-mailu nebo diety..." 
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-medium">
                </div>
                <div class="flex flex-wrap gap-2">
                    <select id="filter-rsvp" onchange="filterGuestsTable()" class="px-3 py-2 rounded-lg border border-slate-200 text-xs font-bold bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="ALL">Všechny RSVP</option>
                        <option value="ANO">RSVP: Přijde</option>
                        <option value="NE">RSVP: Nepřijde</option>
                    </select>
                    <select id="filter-lunch" onchange="filterGuestsTable()" class="px-3 py-2 rounded-lg border border-slate-200 text-xs font-bold bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="ALL">Všechny obědy</option>
                        <option value="ANO">Na oběd: Ano</option>
                        <option value="NE">Na oběd: Ne</option>
                    </select>
                    <select id="filter-kids" onchange="filterGuestsTable()" class="px-3 py-2 rounded-lg border border-slate-200 text-xs font-bold bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="ALL">Všechny děti</option>
                        <option value="ANO">S dětmi</option>
                    </select>
                    <select id="filter-diet" onchange="filterGuestsTable()" class="px-3 py-2 rounded-lg border border-slate-200 text-xs font-bold bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                        <option value="ALL">Všechny diety</option>
                        <option value="DIET">Pouze s omezením</option>
                    </select>
                </div>
            </div>

            <!-- Table Card -->
            <div class="bg-white rounded-2xl shadow-xs border border-slate-100 overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm" id="guests-table-el">
                        <thead>
                            <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold text-xs uppercase">
                                <th class="p-4">Jméno</th>
                                <th class="p-4">E-mail</th>
                                <th class="p-4 text-center">RSVP</th>
                                <th class="p-4 text-center">Oběd</th>
                                <th class="p-4">Skupina</th>
                                <th class="p-4">Děti</th>
                                <th class="p-4">Dieta</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 font-medium">
                            <!-- Injected by JavaScript template inside python -->
                            {"".join([f'''
                            <tr class="guest-row" 
                                data-name="{g['name'].lower()}" 
                                data-email="{g['email'].lower()}" 
                                data-rsvp="{g['rsvp'].upper()}" 
                                data-lunch="{g['lunch'].upper()}" 
                                data-kids="{g['kids'].upper()}" 
                                data-diet="{('yes' if g['diet'] else 'no')}"
                                data-all-text="{g['name'].lower()} {g['email'].lower()} {g['diet'].lower()}">
                                <td class="p-4 text-slate-900 font-bold">{g['name']}</td>
                                <td class="p-4 text-slate-500 text-xs font-mono">{g['email']}</td>
                                <td class="p-4 text-center">
                                    <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-bold { 'bg-emerald-50 text-emerald-700' if g['rsvp'].lower() == 'ano' else 'bg-rose-50 text-rose-700' }">
                                        {g['rsvp']}
                                    </span>
                                </td>
                                <td class="p-4 text-center">
                                    { f'<span class="inline-block bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-xs font-bold">Oběd</span>' if g['lunch'].lower() == 'ano' else '<span class="text-slate-300 text-xs">-</span>' }
                                </td>
                                <td class="p-4 text-slate-600 text-xs">{g['family'] if g['family'] else 'Ostatní'}</td>
                                <td class="p-4">
                                    { f'<span class="text-xs text-amber-700 font-semibold block">{g["kids_detail"]}</span>' if g['kids'].lower() == 'ano' else '<span class="text-slate-300 text-xs">-</span>' }
                                </td>
                                <td class="p-4">
                                    { f'<span class="text-xs bg-rose-50 text-rose-700 border border-rose-100 px-2 py-0.5 rounded font-semibold">{g["diet"]}</span>' if g['diet'] else '<span class="text-slate-300 text-xs">-</span>' }
                                </td>
                            </tr>
                            ''' for g in guests_list])}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- 3. SONGS TAB -->
        <section id="tab-songs" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
                <h2 class="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">🎵 Písničky na přání</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {"".join([f'''
                    <div class="p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-indigo-50/30 hover:border-indigo-100 transition-all">
                        <span class="font-bold text-slate-800 block text-sm">{item['song']}</span>
                        {f'<a href="{item["link"]}" target="_blank" class="mt-2 text-xs text-indigo-600 hover:underline inline-flex items-center gap-1 font-semibold break-all">{item["link"]} ↗</a>' if item['link'] else '<span class="text-xs text-slate-400 italic block mt-1">Bez odkazu</span>'}
                    </div>
                    ''' for item in songs_list]) if songs_list else '<div class="col-span-full text-slate-400 text-sm text-center py-12 font-medium">Zatím nebyly nahlášeny žádné písničky.</div>'}
                </div>
            </div>
        </section>

        <!-- 4. MESSAGES TAB -->
        <section id="tab-messages" class="tab-content space-y-6 hidden">
            <div class="bg-white p-6 rounded-2xl shadow-xs border border-slate-100">
                <h2 class="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">✉️ Vzkazy v morseovce</h2>
                <div class="space-y-4 max-w-3xl">
                    {"".join([f'''
                    <div class="p-5 rounded-2xl border border-slate-100 bg-slate-50 hover:bg-slate-100/50 transition-all">
                        <div class="flex justify-between items-center mb-3">
                            <span class="font-bold text-slate-900 text-sm">{item['name']}</span>
                            <span class="text-[10px] font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-2 py-0.5 rounded">Vzkaz</span>
                        </div>
                        <p class="text-xs font-mono bg-white p-3 border border-slate-100 rounded-xl mb-3 text-slate-500 overflow-x-auto whitespace-nowrap scrollbar-none italic">
                            {item['morse']}
                        </p>
                        <p class="text-slate-800 font-semibold text-sm leading-relaxed pl-2 border-l-2 border-indigo-500">
                            {item['decoded']}
                        </p>
                    </div>
                    ''' for item in messages_list]) if messages_list else '<div class="text-slate-400 text-sm text-center py-12 font-medium">Zatím nebyly zaslány žádné vzkazy.</div>'}
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="mt-12 pt-6 border-t border-slate-200 text-center text-xs text-slate-400 font-semibold">
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
                btn.classList.remove('border-indigo-600', 'text-indigo-600');
                btn.classList.add('border-transparent', 'text-slate-500');
            }});
            
            // Activate selected tab button indicator
            const activeBtn = document.getElementById('btn-' + tabId);
            activeBtn.classList.remove('border-transparent', 'text-slate-500');
            activeBtn.classList.add('border-indigo-600', 'text-indigo-600');
        }}

        function filterGuestsTable() {{
            const searchQuery = document.getElementById('guest-search').value.toLowerCase().trim();
            const rsvpFilter = document.getElementById('filter-rsvp').value;
            const lunchFilter = document.getElementById('filter-lunch').value;
            const kidsFilter = document.getElementById('filter-kids').value;
            const dietFilter = document.getElementById('filter-diet').value;

            document.querySelectorAll('.guest-row').forEach(row => {{
                const allText = row.getAttribute('data-all-text') || '';
                const rsvp = row.getAttribute('data-rsvp') || '';
                const lunch = row.getAttribute('data-lunch') || '';
                const kids = row.getAttribute('data-kids') || '';
                const diet = row.getAttribute('data-diet') || '';

                // Search query match
                const matchSearch = searchQuery === '' || allText.includes(searchQuery);

                // Filters match
                const matchRsvp = rsvpFilter === 'ALL' || rsvp === rsvpFilter;
                const matchLunch = lunchFilter === 'ALL' || lunch === lunchFilter;
                const matchKids = kidsFilter === 'ALL' || kids === kidsFilter;
                const matchDiet = dietFilter === 'ALL' || (dietFilter === 'DIET' && diet === 'yes');

                if (matchSearch && matchRsvp && matchLunch && matchKids && matchDiet) {{
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
