"""
Scrape LabMaus team data using Selenium for JavaScript-rendered content
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

print(">>> Starting scrape_labmaus.py...")

DB_PATH = Path(__file__).resolve().parent / "professor_sequoia.db"

# Regulation mapping (what LabMaus calls them)
REGULATIONS = {
    'A': 'Scarlet & Violet - Regulation A',
    'B': 'Scarlet & Violet - Regulation B', 
    'C': 'Scarlet & Violet - Regulation C',
    'D': 'Scarlet & Violet - Regulation D',
    'E': 'Scarlet & Violet - Regulation E',
    'F': 'Scarlet & Violet - Regulation F',
    'G': 'Scarlet & Violet - Regulation G',
    'H': 'Scarlet & Violet - Regulation H',
    'I': 'Scarlet & Violet - Regulation I',
    'J': 'Scarlet & Violet - Regulation J',
}


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


def scrape_regulation_teams(driver, regulation_letter):
    """
    Scrape team data for a specific regulation using Selenium.
    """
    print(f"\nScraping Regulation {regulation_letter}...")
    
    url = "https://labmaus.net/teams"
    driver.get(url)
    
    try:
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        # Find and click the regulation dropdown
        # You'll need to inspect the actual element - this is an example
        regulation_dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Scarlet & Violet')]"))
        )
        regulation_dropdown.click()
        time.sleep(1)
        
        # Select the specific regulation
        reg_name = REGULATIONS[regulation_letter]
        regulation_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//div[contains(text(), '{reg_name}')]"))
        )
        regulation_option.click()
        time.sleep(2)
        
        # Click search button
        search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
        search_button.click()
        time.sleep(3)
        
        # Now extract the team data from __NEXT_DATA__ script tag
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script_tag:
            print(f"  [!] No team data found for Regulation {regulation_letter}")
            return []
        
        data = json.loads(script_tag.string)
        teams = data['props']['pageProps']['teams']
        
        print(f"  → Found {len(teams)} teams")
        return teams
        
    except Exception as e:
        print(f"  [!] Error scraping Regulation {regulation_letter}: {e}")
        return []


def aggregate_pokemon_usage(teams):
    """Calculate usage statistics from team data."""
    if not teams:
        return []
    
    pokemon_counts = defaultdict(int)
    total_slots = 0
    
    for team in teams:
        for pokemon in team.get('team', []):
            name = pokemon.get('species', 'Unknown').lower()
            name = name.replace(' ', '-')
            pokemon_counts[name] += 1
            total_slots += 1
    
    if total_slots == 0:
        return []
    
    usage_list = []
    for pokemon_name, count in pokemon_counts.items():
        usage_percent = (count / total_slots) * 100
        usage_list.append({
            'pokemon_name': pokemon_name,
            'usage_percent': round(usage_percent, 2),
            'count': count
        })
    
    usage_list.sort(key=lambda x: x['count'], reverse=True)
    for rank, item in enumerate(usage_list, 1):
        item['rank'] = rank
    
    print(f"  ✓ Calculated usage for {len(usage_list)} unique Pokémon")
    if usage_list:
        top_5 = ', '.join([f"{u['pokemon_name']} ({u['usage_percent']:.1f}%)" for u in usage_list[:5]])
        print(f"  Top 5: {top_5}")
    
    return usage_list


def scrape_all_regulations():
    """Scrape usage data for all regulations."""
    driver = setup_driver()
    all_usage = {}
    
    try:
        for reg_letter in REGULATIONS.keys():
            print(f"\n{'='*60}")
            teams = scrape_regulation_teams(driver, reg_letter)
            
            if teams:
                usage = aggregate_pokemon_usage(teams)
                if usage:
                    all_usage[f'reg-{reg_letter.lower()}'] = usage
                    print(f"  ✓ Successfully processed Regulation {reg_letter}")
            else:
                print(f"  ⚠️  No data for Regulation {reg_letter}")
            
            time.sleep(2)  # Be nice to the server
    
    finally:
        driver.quit()
        print("\n  ✓ Browser closed")
    
    return all_usage


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
    print("LabMaus Selenium Scraper")
    print("="*60)
    
    all_usage = scrape_all_regulations()
    
    if all_usage:
        populate_usage_to_db(all_usage)
        print("\n✅ Scraping complete!")
    else:
        print("\n❌ No data scraped - check if site structure has changed")