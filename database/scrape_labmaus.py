"""
Scrape LabMaus Pokémon usage data by directly accessing Pokemon pages
"""

import sqlite3
import time
import json
from pathlib import Path
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

print(">>> Starting LabMaus Pokémon usage scraper...")

DB_PATH = Path(__file__).resolve().parent / "professor_sequoia.db"

# Top competitive Pokémon to search for
POKEMON_TO_SEARCH = [
    'incineroar', 'rillaboom', 'amoonguss', 'tornadus', 'landorus-therian',
    'urshifu-rapid-strike', 'calyrex-shadow', 'ogerpon-wellspring', 'farigiraf',
    'gholdengo', 'kingambit', 'whimsicott', 'pelipper', 'archaludon',
    'iron-hands', 'sneasler', 'ursaluna-bloodmoon', 'annihilape', 'tatsugiri',
    'dondozo', 'iron-crown', 'clefairy', 'corviknight', 'arcanine', 'garganacl',
    'porygon2', 'dragonite', 'gastrodon', 'goodra-hisui', 'grimmsnarl',
    'iron-boulder', 'kommo-o', 'lilligant-hisui', 'maushold', 'meowscarada',
    'ninetales-alola', 'palafin', 'primarina', 'reuniclus', 'scream-tail',
    'smeargle', 'sylveon', 'tapu-fini', 'ting-lu', 'torkoal', 'volcarona',
    'baxcalibur', 'entei', 'heatran', 'indeedee', 'walking-wake',
    'iron-bundle', 'wo-chien', 'great-tusk', 'ursaluna', 'chi-yu',
    'chien-pao', 'raging-bolt', 'gouging-fire', 'iron-valiant', 'flutter-mane',
    'roaring-moon', 'iron-treads', 'iron-moth', 'iron-jugulis', 'sandy-shocks',
    'brute-bonnet', 'slither-wing', 'scream-tail', 'iron-thorns', 'iron-bundle'
]

REGULATIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']


def setup_driver():
    """Setup headless Chrome driver."""
    print("Setting up Chrome driver...")
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("  ✓ Chrome driver ready")
    return driver


def get_pokemon_url_name(pokemon_name):
    """Convert Pokemon name to URL format."""
    # LabMaus uses lowercase with hyphens
    return pokemon_name.lower().replace(' ', '-')


def scrape_pokemon_page(driver, pokemon_name):
    """
    Access Pokemon page directly and extract usage data.
    """
    url_name = get_pokemon_url_name(pokemon_name)
    url = f"https://labmaus.net/pokemon/{url_name}"
    
    print(f"\nScraping {pokemon_name} from {url}...")
    
    try:
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        # Get page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        usage_data = {}
        
        # Look for __NEXT_DATA__ script tag
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                props = data.get('props', {}).get('pageProps', {})
                
                # Print structure for debugging (first pokemon only)
                if pokemon_name == POKEMON_TO_SEARCH[0]:
                    print(f"  → Page props keys: {list(props.keys())}")
                
                # Look for usage data in various possible locations
                pokemon_data = props.get('pokemon', props.get('data', props))
                
                # Check if there's regulation-specific data
                if 'regulations' in pokemon_data:
                    for reg_data in pokemon_data['regulations']:
                        # Extract regulation letter
                        reg_name = str(reg_data.get('name', reg_data.get('regulation', '')))
                        match = re.search(r'Regulation ([A-J])', reg_name, re.IGNORECASE)
                        
                        if match:
                            reg_letter = match.group(1).upper()
                            usage_pct = float(reg_data.get('usage', reg_data.get('usagePercent', 0)))
                            
                            if usage_pct > 0:
                                usage_data[f'reg-{reg_letter.lower()}'] = usage_pct
                
                # Alternative structure: direct regulation keys
                for reg in REGULATIONS:
                    for key_pattern in [f'reg{reg}', f'regulation{reg}', f'reg-{reg.lower()}', f'regulation_{reg.lower()}']:
                        if key_pattern in pokemon_data:
                            reg_info = pokemon_data[key_pattern]
                            if isinstance(reg_info, dict) and 'usage' in reg_info:
                                usage_data[f'reg-{reg.lower()}'] = float(reg_info['usage'])
                            elif isinstance(reg_info, (int, float)):
                                usage_data[f'reg-{reg.lower()}'] = float(reg_info)
                
                if usage_data:
                    print(f"  ✓ Found usage for {len(usage_data)} regulations")
                    return usage_data
                
            except json.JSONDecodeError as e:
                print(f"  [!] JSON decode error: {e}")
            except Exception as e:
                print(f"  [!] Error parsing data: {e}")
        
        # Fallback: scrape visible HTML
        print(f"  → Trying HTML scraping fallback...")
        
        # Look for tables or divs with regulation data
        for reg in REGULATIONS:
            patterns = [
                f'Regulation {reg}',
                f'Reg {reg}',
                f'Series {reg}'
            ]
            
            for pattern in patterns:
                # Find all text containing this regulation
                elements = soup.find_all(string=lambda text: text and pattern in str(text))
                
                for elem in elements:
                    # Look in parent element for percentage
                    parent = elem.parent
                    if parent:
                        parent_text = parent.get_text()
                        # Look for percentage near regulation name
                        pct_match = re.search(r'(\d+\.?\d*)\s*%', parent_text)
                        if pct_match:
                            usage_pct = float(pct_match.group(1))
                            if usage_pct > 0:
                                usage_data[f'reg-{reg.lower()}'] = usage_pct
                                break
        
        if usage_data:
            print(f"  ✓ Found usage for {len(usage_data)} regulations (HTML scraping)")
        else:
            print(f"  ⚠️  No usage data found")
            # Save page for debugging
            with open(f"debug_{url_name}.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print(f"  → Saved debug_{url_name}.html for inspection")
        
        return usage_data
        
    except Exception as e:
        print(f"  [!] Error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def scrape_all_pokemon_usage():
    """Scrape usage for all competitive Pokémon."""
    driver = setup_driver()
    all_usage = defaultdict(list)
    
    try:
        for i, pokemon in enumerate(POKEMON_TO_SEARCH, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(POKEMON_TO_SEARCH)}] {pokemon}")
            print('='*60)
            
            usage_data = scrape_pokemon_page(driver, pokemon)
            
            if usage_data:
                # Organize by regulation
                for reg_id, usage_pct in usage_data.items():
                    all_usage[reg_id].append({
                        'pokemon_name': pokemon,
                        'usage_percent': usage_pct,
                    })
            
            time.sleep(1)  # Be nice to the server
    
    finally:
        driver.quit()
        print("\n  ✓ Browser closed")
    
    # Calculate ranks for each regulation
    for reg_id in all_usage:
        all_usage[reg_id].sort(key=lambda x: x['usage_percent'], reverse=True)
        for rank, pokemon in enumerate(all_usage[reg_id], 1):
            pokemon['rank'] = rank
    
    return dict(all_usage)


def populate_usage_to_db(all_usage, month='2025-01'):
    """Populate usage statistics in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("Populating database...")
    print("="*60)
    
    total_added = 0
    for reg_id, usage_list in all_usage.items():
        for entry in usage_list:
            cursor.execute('''
                INSERT OR REPLACE INTO usage_stats
                (pokemon_name, regulation_id, usage_percent, rank, month)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                entry['pokemon_name'],
                reg_id,
                entry['usage_percent'],
                entry['rank'],
                month
            ))
            total_added += 1
        
        print(f"  → Added {len(usage_list)} Pokémon for {reg_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n  ✓ Total: {total_added} usage statistics added")


if __name__ == "__main__":
    print("="*60)
    print("LabMaus Pokémon Usage Scraper (Direct URLs)")
    print("="*60)
    
    all_usage = scrape_all_pokemon_usage()
    
    if all_usage:
        populate_usage_to_db(all_usage)
        
        # Print summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        for reg_id in sorted(all_usage.keys()):
            print(f"\n{reg_id.upper()}: {len(all_usage[reg_id])} Pokémon")
            top_5 = all_usage[reg_id][:5]
            for p in top_5:
                print(f"  {p['rank']}. {p['pokemon_name']}: {p['usage_percent']:.1f}%")
        
        print("\n✅ Scraping complete!")
    else:
        print("\n❌ No data scraped")
        print("Check the debug_*.html files to see the page structure")