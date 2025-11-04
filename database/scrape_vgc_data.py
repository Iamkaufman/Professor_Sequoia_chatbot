"""
Scrape VGC regulations and usage stats from external sources (Victory Road + LabMaus)
"""

import sqlite3
import requests
import json
import time
from bs4 import BeautifulSoup
import re
from pathlib import Path
import certifi
import urllib3
from collections import defaultdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_PATH = Path(__file__).resolve().parent / "professor_sequoia.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
#  SCRAPE REGULATIONS FROM VICTORY ROAD
# ---------------------------------------------------------------------------
def scrape_victory_road_regulations():
    """Scrape regulation data from Victory Road."""
    print("Scraping regulations from Victory Road...")

    url = "https://victoryroad.pro/sv-rules-regulations/"
    try:
        response = requests.get(url, timeout=10, verify=certifi.where())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        regulations = []
        reg_sections = soup.find_all(["h2", "h3"], string=re.compile(r"Regulation [A-Z]", re.IGNORECASE))

        for section in reg_sections:
            reg_name = section.get_text().strip()
            reg_id_match = re.search(r"Regulation ([A-Z])", reg_name, re.IGNORECASE)
            if not reg_id_match:
                continue

            reg_letter = reg_id_match.group(1).upper()
            reg_id = f"reg-{reg_letter.lower()}"

            # Extract date range
            content = []
            for sibling in section.find_next_siblings():
                if sibling.name in ["h2", "h3"] and "regulation" in sibling.get_text().lower():
                    break
                content.append(sibling.get_text())

            text_block = " ".join(content)
            description = " ".join(content[:3]) if content else ""

            date_match = re.search(
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:to|through|-)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                text_block,
            )
            start_date = date_match.group(1) if date_match else ""
            end_date = date_match.group(2) if date_match else ""

            regulations.append(
                {
                    "regulation_id": reg_id,
                    "name": reg_name,
                    "description": description[:500],
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

        print(f"  → Found {len(regulations)} regulations")
        return regulations

    except Exception as e:
        print(f"  [!] Error scraping Victory Road: {e}")
        return []


# ---------------------------------------------------------------------------
#  LABMAUS USAGE FETCHER
# ---------------------------------------------------------------------------
BASE_URL = "https://labmaus.net/teams?regulation={}"

def get_team_data(reg_letter: str):
    """Fetch and parse team data for a given regulation (A–J)."""
    url = BASE_URL.format(reg_letter)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # Disable SSL verification since certifi.where() isn't working
        response = requests.get(url, headers=headers, verify=False, timeout=10)

        if response.status_code != 200:
            print(f"  [!] Failed to fetch regulation {reg_letter}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for embedded JSON script tag
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script_tag:
            print(f"  [!] No team data found for Regulation {reg_letter}")
            return []

        data = json.loads(script_tag.string)
        teams = data["props"]["pageProps"]["teams"]
        print(f"  → Found {len(teams)} teams for Regulation {reg_letter}")
        return teams
        
    except KeyError:
        print(f"  [!] Could not parse team data for Regulation {reg_letter}")
        return []
    except Exception as e:
        print(f"  [!] Error fetching Regulation {reg_letter}: {e}")
        return []


def aggregate_pokemon_usage(regulation_letter='H'):
    """
    Aggregate Pokémon usage for a specific regulation.
    Returns list of dicts with pokemon_name, usage_percent, and rank.
    """
    print(f"\nAggregating usage for Regulation {regulation_letter}...")
    
    teams = get_team_data(regulation_letter)
    if not teams:
        print(f"  [!] No teams found for Regulation {regulation_letter}")
        return []
    
    pokemon_counts = defaultdict(int)
    total_slots = 0
    
    for team in teams:
        for pokemon in team.get("team", []):
            name = pokemon.get("species", "Unknown").lower()
            # Normalize names (e.g., remove spaces, convert to hyphens)
            name = name.replace(" ", "-")
            pokemon_counts[name] += 1
            total_slots += 1
    
    if total_slots == 0:
        return []
    
    # Calculate percentages and rank
    usage_list = []
    for pokemon_name, count in pokemon_counts.items():
        usage_percent = (count / total_slots) * 100
        usage_list.append({
            'pokemon_name': pokemon_name,
            'usage_percent': round(usage_percent, 2),
            'count': count
        })
    
    # Sort by usage and add rank
    usage_list.sort(key=lambda x: x['count'], reverse=True)
    for rank, item in enumerate(usage_list, 1):
        item['rank'] = rank
    
    print(f"  ✓ Calculated usage for {len(usage_list)} unique Pokémon")
    if usage_list:
        top_5 = ', '.join([f"{u['pokemon_name']} ({u['usage_percent']:.1f}%)" for u in usage_list[:5]])
        print(f"  Top 5: {top_5}")
    
    return usage_list


def get_all_regulations_usage():
    """Get usage data for all regulations A-J."""
    all_usage = {}
    regulations = [chr(i) for i in range(ord('A'), ord('K'))]  # A–J
    
    print("\n" + "="*60)
    print("Fetching usage data for all regulations (A-J)")
    print("This will take approximately 10-15 minutes...")
    print("="*60)
    
    for i, reg in enumerate(regulations, 1):
        print(f"\n[{i}/{len(regulations)}] Processing Regulation {reg}...")
        usage = aggregate_pokemon_usage(reg)
        if usage:
            all_usage[f'reg-{reg.lower()}'] = usage
            print(f"  ✓ Successfully processed Regulation {reg}")
        else:
            print(f"  ⚠️  No data for Regulation {reg}")
        
        # Be nice to the server - wait between requests
        if i < len(regulations):
            print(f"  Waiting 2 seconds before next request...")
            time.sleep(2)
    
    return all_usage


# ---------------------------------------------------------------------------
#  DATABASE POPULATION
# ---------------------------------------------------------------------------
def populate_regulations_to_db(conn, regulations):
    """Add regulations to database."""
    cursor = conn.cursor()
    
    print("\nPopulating regulations table...")
    for reg in regulations:
        cursor.execute('''
            INSERT OR REPLACE INTO regulations
            (regulation_id, name, description, allowed_pokemon, restricted_pokemon, 
             banned_pokemon, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reg.get('regulation_id', ''),
            reg.get('name', ''),
            reg.get('description', ''),
            reg.get('allowed_pokemon', ''),
            reg.get('restricted_pokemon', ''),
            reg.get('banned_pokemon', ''),
            reg.get('start_date', ''),
            reg.get('end_date', '')
        ))
    
    conn.commit()
    print(f"  ✓ Added {len(regulations)} regulations to database")


def populate_usage_to_db(conn, all_usage, month='2025-01'):
    """Add usage stats to database for all regulations."""
    cursor = conn.cursor()
    
    print("\nPopulating usage statistics...")
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
    print(f"  ✓ Total: {total_added} usage statistics added to database")


def print_summary(conn):
    """Print summary statistics."""
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    
    # Count regulations
    cursor.execute("SELECT COUNT(*) FROM regulations")
    reg_count = cursor.fetchone()[0]
    print(f"Regulations: {reg_count}")
    
    # Count usage stats by regulation
    cursor.execute("""
        SELECT regulation_id, COUNT(*) 
        FROM usage_stats 
        GROUP BY regulation_id 
        ORDER BY regulation_id
    """)
    
    print("\nUsage statistics by regulation:")
    for reg_id, count in cursor.fetchall():
        print(f"  {reg_id}: {count} Pokémon")
    
    # Show top 10 for current regulation (reg-h)
    cursor.execute("""
        SELECT pokemon_name, usage_percent, rank 
        FROM usage_stats 
        WHERE regulation_id = 'reg-h' 
        ORDER BY rank 
        LIMIT 10
    """)
    
    print("\nTop 10 Pokémon in Regulation H:")
    for name, usage, rank in cursor.fetchall():
        print(f"  {rank}. {name.title()}: {usage}%")


# ---------------------------------------------------------------------------
#  MAIN EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("VGC Data Scraper - Victory Road + LabMaus")
    print("Full Population Mode (All Regulations A-J)")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Step 1: Scrape regulations from Victory Road
    print("STEP 1: Scraping Victory Road for regulations...")
    print("="*60)
    regulations = scrape_victory_road_regulations()
    if regulations:
        populate_regulations_to_db(conn, regulations)
    else:
        print("  ⚠️  No regulations found, skipping...")
    
    # Step 2: Scrape usage from LabMaus for ALL regulations
    print("\n" + "=" * 60)
    print("STEP 2: Scraping LabMaus for usage data (ALL REGULATIONS)")
    print("=" * 60)
    
    all_usage = get_all_regulations_usage()
    
    if all_usage:
        populate_usage_to_db(conn, all_usage)
        print_summary(conn)
    else:
        print("\n  ⚠️  Could not fetch any usage data from LabMaus")
        print("  Recommendation: Check if the site structure has changed")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ VGC data scraping complete!")
    print("=" * 60)