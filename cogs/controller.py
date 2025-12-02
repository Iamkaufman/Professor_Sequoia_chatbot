import re
import sys
import os
import asyncio
import random
from typing import List, Dict, Any
import importlib
import discord
from database import repository
import requests
from collections import  Counter

# --- Import dependencies ---
from database.repository import Repository
from core.nlp import parse_buildcore_message, needs_clarification

repo = Repository()

# Competitive Regulation Definitions
REGULATIONS = {
    "A": {
        "banned": [
            "charmander", "charmeleon", "charizard", "meowth-galar", "wooper", "quagsire",
            # Paradox Pokémon - ALL BANNED IN REG A
            "great-tusk", "brute-bonnet", "flutter-mane", "slither-wing", "sandy-shocks", "roaring-moon",
            "iron-treads", "iron-moth", "iron-hands", "iron-jugulis", "iron-thorns", "iron-bundle", "iron-valiant",
            # Treasures of Ruin
            "chi-yu", "chien-pao", "wo-chien", "ting-lu",
            # Box legendaries
            "koraidon", "miraidon"
        ]
    },
    "B": {
        "inherits": "A",
        "remove_bans": ["great-tusk", "brute-bonnet", "flutter-mane", "slither-wing", "sandy-shocks", "roaring-moon",
            "iron-treads", "iron-moth", "iron-hands", "iron-jugulis", "iron-thorns", "iron-bundle", "iron-valiant"]
    },
    "C": {
        "inherits": "B",
        "remove_bans": ["chi-yu", "ting-lu", "chien-pao", "wo-chien"]
    },
    "D": {
        "inherits": "C",
        "remove_bans": ["walking-wake", "iron-leaves"],
        "add_bans": ["gouging-fire", "iron-crown", "raging-bolt", "iron-boulder"]
    },
    "E": {
        "inherits": "D",
        "remove_bans": ["ogerpon", "ogerpon-wellspring", "ogerpon-hearthflame", "ogerpon-cornerstone",
                        "dipplin", "fezandipiti", "okidogi", "munkidori"]
    },
    "F": {
        "inherits": "E",
        "remove_bans": ["archaludon", "hydrapple", "terapagos", "raging-bolt", "iron-crown", 
                        "iron-boulder", "gouging-fire"]
    },
    "G": {
        "inherits": "F",
        "restricted_limit": 1
    },
    "H": {
        # Reg H is special - goes back to stricter rules
        "banned": [
            # ALL Paradox Pokémon banned
            "great-tusk", "scream-tail", "brute-bonnet", "flutter-mane", "slither-wing", 
            "sandy-shocks", "roaring-moon",
            "iron-treads", "iron-bundle", "iron-hands", "iron-jugulis", "iron-moth", 
            "iron-thorns", "iron-valiant",
            "walking-wake", "iron-leaves", "gouging-fire", "raging-bolt", 
            "iron-boulder", "iron-crown",
            # Box legendaries
            "Articuno", "Zapdos", "Moltres", "Mewtwo", "Raikou", "Entei", "Suicune", "Articuno-Galar",
            "Zapdos-Galar", "Moltres-Galar", "Lugia", "Ho-Oh", "Regirock", "Regice", "Registeel", "latias",
            "latios", "Kyogre", "Groudon", "Rayquaza", "Uxie", "Mesprit", "Azelf", "Dialga", "Palkia",
            # Treasures still banned
            "chi-yu", "chien-pao", "wo-chien", "ting-lu"
        ]
    },
    "I": {
        "inherits": "G",
        "restricted_limit": 2
    },
    "J": {
        "inherits": "I",
        "mythical_allowed": True
    },
}

def get_regulation_list(reg_name: str):
    """Resolve a regulation definition recursively."""
    reg = REGULATIONS.get(reg_name)
    if not reg:
        return {"allowed": [], "banned": []}

    allowed = set()
    banned = set()
    
    if "inherits" in reg:
        base = get_regulation_list(reg["inherits"])
        allowed.update(base.get("allowed", []))
        banned.update(base.get("banned", []))

    allowed.update(reg.get("add", []))
    banned.update(reg.get("banned", []))
    
    # Remove allowed from banned
    banned = banned - allowed
    
    return {"allowed": list(allowed), "banned": list(banned)}
async def handle_buildcore_request(raw_message: str, user_id: str, regulation: str = "H") -> Dict[str, Any]:
    """
    Build a competitive VGC team around core Pokémon.
    Uses usage statistics and regulation legality.
    """
    parsed = parse_buildcore_message(raw_message)

    # At the beginning of the function
    if not raw_message or not raw_message.strip():
        return {
            'status': 'clarify',
            'message': "I didn't catch which Pokémon to build around. Please tell me one or two core Pokémon."
        }
    # --- Parse regulation from message if specified ---
    reg_match = re.search(r'\breg[- ]?([a-j])\b', raw_message.lower())
    if reg_match:
        regulation = reg_match.group(1).upper()
    
    print(f"🎮 Building for Regulation {regulation}")

    # --- Fallback parser ---
    if parsed.get('intent') != 'build_core' or not parsed.get('pokemons'):
        text = re.sub(r"[^a-zA-Z0-9\s,\-]", " ", raw_message).lower()
        all_names = await repo.get_all_pokemon_names()
        matches = [name for name in all_names if name in text]

        if matches:
            parsed['pokemons'] = list(dict.fromkeys(matches))
            parsed['intent'] = 'build_core'
        else:
            parts = text.split("buildcore", 1)
            if len(parts) > 1:
                pokes = [p.strip() for p in re.split(r"[,\s]+", parts[1]) if p.strip()]
                parsed['pokemons'] = pokes
                parsed['intent'] = 'build_core'

    if parsed.get('intent') != 'build_core':
        return {'status': 'error', 'message': "I couldn't detect a build request in your message."}

    if needs_clarification(parsed):
        return {
            'status': 'clarify',
            'message': "I didn't catch which Pokémon to build around. Please specify 1-2 core Pokémon."
        }

    # --- Resolve core Pokémon ---
    resolved = []
    for p in parsed['pokemons']:
        info = await repo.get_pokemon_by_name(p)
        if info:
            resolved.append(info)
            continue
        candidates = await repo.search_pokemon_by_partial(p, limit=5)
        if candidates:
            resolved.append(candidates[0])
        else:
            return {'status': 'clarify', 'message': f"I couldn't find `{p}` in my database."}

    # --- Check if core Pokémon are legal ---
    reg_rules = get_regulation_list(regulation)
    banned_names = [b.lower() for b in reg_rules.get('banned', [])]
    
    illegal_core = [p['name'] for p in resolved if p['name'].lower() in banned_names]
    if illegal_core:
        return {
            'status': 'error',
            'message': f"❌ The following Pokémon are banned in Regulation {regulation}: {', '.join(illegal_core)}"
        }

    team = list(resolved)
    core_ids = [p['pokemon_id'] for p in resolved]

    # --- Get usage statistics for this regulation ---
    usage_stats = await repo.get_common_usage(f'reg-{regulation.lower()}')

    # Check if usage_stats is actually a list/dict we can work with
    if not usage_stats or not isinstance(usage_stats, (list, dict)):
        print(f"⚠️ No usage stats found for reg-{regulation.lower()}, using all Pokémon")
        pool = await repo.query_pokemon_pool(exclude_ids=core_ids, limit=200)
    else:
        # If it's a list, limit to 100
        if isinstance(usage_stats, list):
            usage_stats = usage_stats[:100]
    
        # Filter pool to only include legal, high-usage Pokémon
        pool = []
        # ... rest of your existing code ...
    
    if not usage_stats:
        print(f"⚠️ No usage stats found for reg-{regulation.lower()}, using all Pokémon")
        pool = await repo.query_pokemon_pool(exclude_ids=core_ids, limit=200)
    else:
        # Filter pool to only include legal, high-usage Pokémon
        pool = []
        for stat in usage_stats:
            poke_name = stat['pokemon_name']
            
            # Skip if banned
            if poke_name in banned_names:
                continue
            
            # Skip if already in team
            if any(p['name'].lower() == poke_name for p in team):
                continue
            
            # Get full Pokémon data
            poke_data = await repo.get_pokemon_by_name(poke_name)
            if poke_data:
                poke_data['usage_rank'] = stat['rank']
                poke_data['usage_percent'] = stat['usage_percent']
                pool.append(poke_data)
            
            if len(pool) >= 100:
                break

    if not pool:
        return {'status': 'error', 'message': "Could not find any legal Pokémon to complete the team."}

    # --- Score candidates based on synergy + usage ---
    core_types = set()
    for p in resolved:
        if p.get('type1'):
            core_types.add(p['type1'])
        if p.get('type2'):
            core_types.add(p['type2'])
    core_types.discard(None)

    def score_candidate(cand):
        score = 0
        
        # Usage-based scoring (higher usage = better)
        if 'usage_rank' in cand:
            score += (100 - cand['usage_rank']) * 2  # Top picks get big boost
        
        # Type synergy
        types = {cand.get('type1'), cand.get('type2')}
        types.discard(None)
        
        strength = {
            'fire': ['grass', 'ice', 'bug', 'steel'],
            'water': ['fire', 'ground', 'rock'],
            'electric': ['water', 'flying'],
            'grass': ['water', 'ground', 'rock'],
            'ice': ['dragon', 'flying', 'grass', 'ground'],
            'fighting': ['normal', 'rock', 'steel', 'ice', 'dark'],
            'ground': ['fire', 'electric', 'poison', 'rock', 'steel'],
            'psychic': ['fighting', 'poison'],
            'dark': ['psychic', 'ghost'],
            'ghost': ['psychic', 'ghost'],
            'fairy': ['dragon', 'dark', 'fighting'],
            'dragon': ['dragon'],
        }
        
        for t in types:
            for ct in core_types:
                if ct in strength.get(t, []):
                    score += 5
        
        # Speed tier diversity
        speed = cand.get('spe', 0)
        if speed > 100:
            score += 3
        elif speed < 50:
            score += 2  # Trick Room viability
        
        return score

    # Sort and select
    scored = sorted(pool, key=score_candidate, reverse=True)
    picks = scored[:max(0, 6 - len(team))]
    team.extend(picks)

    # --- Assign realistic moves, items, and EVs ---
    for member in team:
        moves = await repo.get_moves_for_pokemon(member['pokemon_id'])
        
        # Filter to only legal competitive moves
        legal_moves = [
            m for m in moves
            if m.get('power') and m.get('power') > 0 and m['power'] < 200  # No gimmick moves
            and m.get('category') in ['physical', 'special']
            and m.get('name') not in ['self-destruct', 'explosion', 'hyper-beam', 'giga-impact']
        ]
        
        # Sort by power but prioritize STAB
        def move_score(m):
            score = m.get('power', 0)
            move_type = m.get('type', '')
            if move_type == member.get('type1') or move_type == member.get('type2'):
                score += 30  # STAB bonus
            return score
        
        legal_moves.sort(key=move_score, reverse=True)
        member['suggested_moves'] = [m['name'] for m in legal_moves[:4]]
        
        # Better item selection
        speed = member.get('spe', 0)
        if speed > 100:
            member['suggested_item'] = "Choice Scarf" if speed < 120 else "Life Orb"
        elif speed < 50:
            member['suggested_item'] = "Assault Vest"
        else:
            member['suggested_item'] = "Sitrus Berry"
        
        # EVs based on stats
        if member.get('atk', 0) > member.get('spa', 0):
            member['suggested_ev'] = "252 Atk / 252 Spe / 4 HP"
        else:
            member['suggested_ev'] = "252 SpA / 252 Spe / 4 HP"

    # --- Build response ---
    response_lines = [f"**Team for Regulation {regulation}** (built around {', '.join([p['name'].title() for p in resolved])}):"]
    for m in team:
        usage_info = f" (#{m.get('usage_rank', '?')} usage)" if 'usage_rank' in m else ""
        response_lines.append(
            f"\n**{m['name'].title()}**{usage_info}\n"
            f"  Moves: {', '.join(m.get('suggested_moves', []))}\n"
            f"  Item: {m.get('suggested_item')} | EVs: {m.get('suggested_ev')}"
        )

    return {'status': 'ok', 'message': '\n'.join(response_lines), 'team': team}

def parse_pokepaste(text):
    """Parse Pokepaste-format team text into structured data (handles optional lines)."""
    team = []
    # Split Pokémon by double newlines
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text.strip()) if b.strip()]

    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue

        # Example: "Maushold-Four @ Wide Lens"
        header = lines[0]
        name, item = (header.split('@') + ["None"])[:2]
        name, item = name.strip(), item.strip()

        poke = {"name": name, "item": item, "moves": []}

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Ability:"):
                poke["ability"] = line.split("Ability:")[1].strip()
            elif line.startswith("Tera Type:"):
                poke["tera_type"] = line.split("Tera Type:")[1].strip()
            elif line.startswith("EVs:"):
                poke["evs"] = line.split("EVs:")[1].strip()
            elif line.startswith("IVs:"):
                poke["ivs"] = line.split("IVs:")[1].strip()
            elif line.endswith("Nature"):
                poke["nature"] = line.replace("Nature", "").strip()
            elif line.startswith("- "):
                move = line.replace("- ", "").strip()
                poke["moves"].append(move)
            elif line.startswith("Level:"):
                poke["level"] = line.split("Level:")[1].strip()
            elif line.startswith("Shiny:"):
                poke["shiny"] = line.split("Shiny:")[1].strip()

        team.append(poke)
    return team

def evaluate_synergy(team, format_regulation="F"):
    """Dynamic synergy evaluation based on typing, speed control, and roles."""
    import collections

    type_coverage = collections.Counter()
    speed_control_moves = {"Tailwind", "Trick Room", "Icy Wind", "Electroweb", "Thunder Wave"}
    setup_moves = {"Calm Mind", "Swords Dance", "Nasty Plot", "Dragon Dance", "Bulk Up"}
    hazards = {"Stealth Rock", "Spikes", "Toxic Spikes"}
    support_moves = {"Follow Me", "Rage Powder", "Helping Hand", "Fake Out", "Redirection"}

    # --- Collect team data ---
    speed_control_found = []
    offensive_types = set()
    defensive_types = set()
    support_found = []
    hazards_found = []

    for p in team:
        name = p.get("name")
        types = p.get("types", [])
        moves = [m.title() for m in p.get("moves", [])]

        for t in types:
            type_coverage[t] += 1

        if any(m in speed_control_moves for m in moves):
            speed_control_found.append(name)

        if any(m in support_moves for m in moves):
            support_found.append(name)

        if any(m in hazards for m in moves):
            hazards_found.append(name)

        # Offense/defense heuristics
        offensive_types.update(types)
        defensive_types.update(types)

    # --- Evaluate roles ---
    summary = f"This team includes {len(team)} Pokémon."

    if len(speed_control_found) > 0:
        summary += f" Speed control found ({', '.join(speed_control_found)})."
    else:
        summary += " No explicit speed control found."

    # --- Identify weaknesses ---
    weaknesses = []
    if not support_found:
        weaknesses.append("Lacks redirection or general support options.")
    if len(speed_control_found) == 0:
        weaknesses.append("No speed control (Tailwind, Trick Room, etc.) detected.")
    if len(offensive_types) < 6:
        weaknesses.append("Limited offensive type coverage; consider diversifying attackers.")
    if type_coverage["Ground"] >= 3:
        weaknesses.append("Multiple Ground weaknesses — consider adding a Flying or Levitate Pokémon.")
    if type_coverage["Fairy"] == 0:
        weaknesses.append("No Fairy coverage — might struggle into Dragon-types.")

    # --- Legality check ---
    legality = get_regulation_list(format_regulation)
    banned = legality["banned"]
    illegal = [p["name"] for p in team if p["name"] in banned]
    if illegal:
        weaknesses.append(f"Illegal Pokémon for Regulation {format_regulation}: {', '.join(illegal)}")

    # --- Role summary ---
    return {
        "summary": summary,
        "weaknesses": weaknesses,
        "type_coverage": dict(type_coverage),
        "speed_control": speed_control_found,
        "support": support_found,
        "hazards": hazards_found
    }

def evaluate_team(pokepaste_text: str) -> str:
    # --- Step 1: Parse Pokémon names and items ---
    pokemon_pattern = r"^([A-Za-z0-9'♀♂\-\s]+)\s*@\s*(.+?)\n"
    pokemon_matches = re.findall(pokemon_pattern, pokepaste_text, re.MULTILINE)
    team = [p[0].strip() for p in pokemon_matches]

    if not team:
        return "Error: No valid Pokémon sets found. Make sure to paste a full team in Pokepaste format."

    # --- Step 2: Extract moves for all Pokémon ---
    move_lines = re.findall(r"^- (.+)$", pokepaste_text, re.MULTILINE)
    move_text = " ".join(move_lines).lower()

    # --- Step 3: Detect Speed Control ---
    speed_control = []
    if "trick room" in move_text:
        speed_control.append("Trick Room")
    if "tailwind" in move_text:
        speed_control.append("Tailwind")
    if "icy wind" in move_text or "electroweb" in move_text or "scary face" in move_text or "bulldoze" in move_text:
        speed_control.append("Speed Control Moves")

    # --- Step 4: Detect Role Distribution ---
    support_moves = ["follow me", "rage powder", "helping hand", "wide guard", "fake out", "parting shot", "snarl"]
    setup_moves = ["swords dance", "nasty plot", "calm mind", "belly drum", "substitute"]
    utility_moves = ["taunt", "will-o-wisp", "spore", "thunder wave", "snarl", "encore", "trick", "knock off"]

    role_counts = Counter()
    for move in move_lines:
        move_lower = move.lower()
        if any(m in move_lower for m in support_moves):
            role_counts["Support"] += 1
        if any(m in move_lower for m in setup_moves):
            role_counts["Setup"] += 1
        if any(m in move_lower for m in utility_moves):
            role_counts["Utility"] += 1

    # --- Step 5: Detect Type Coverage ---
    type_moves = {
        "Fire": ["heat wave", "eruption", "flamethrower", "flare blitz", "fire blast", "lava plume"],
        "Water": ["hydro pump", "surf", "aqua jet", "scald", "waterfall", "ivy cudgel"],
        "Grass": ["energy ball", "giga drain", "leaf storm", "horn leech", "power whip"],
        "Electric": ["thunderbolt", "volt switch", "discharge", "thunderclap"],
        "Ice": ["ice beam", "icy wind", "blizzard", "ice spinner"],
        "Ground": ["earthquake", "earth power", "headlong rush", "stomping tantrum"],
        "Rock": ["rock slide", "stone edge"],
        "Dark": ["knock off", "snarl", "foul play", "wicked blow", "sucker punch"],
        "Fairy": ["dazzling gleam", "moonblast", "play rough"],
        "Psychic": ["psychic", "expanding force", "psyshock"],
        "Dragon": ["draco meteor", "dragon claw", "dragon pulse"],
        "Ghost": ["shadow ball", "shadow claw", "poltergeist"],
        "Steel": ["iron head", "flash cannon", "steel beam"],
        "Fighting": ["close combat", "sacred sword", "drain punch"],
        "Poison": ["sludge bomb", "poison jab"],
        "Flying": ["hurricane", "brave bird", "air slash"],
    }

    coverage = Counter()
    for t, moves in type_moves.items():
        if any(m in move_text for m in moves):
            coverage[t] += 1

    # --- Step 6: Generate Dynamic Insights ---
    report = [f"**Professor Sequoia — Team Evaluation**"]
    report.append(f"\n**Team Summary:** {', '.join(team)}")

    # Speed Control Comments
    if "Trick Room" in speed_control:
        report.append("\n**Speed Control:** This team includes Trick Room. Likely a slow-mode composition.")
        report.append("→ Avoid redundancy; consider Pokémon that can function outside of Trick Room for flexibility.")
    elif "Tailwind" in speed_control:
        report.append("\n**Speed Control:** Tailwind detected. Team benefits from tempo-based speed control.")
    elif "Speed Control Moves" in speed_control:
        report.append("\n**Speed Control:** Uses moves like Icy Wind or Electroweb for speed control.")
    else:
        report.append("\n**Speed Control:** None detected — consider adding Tailwind, Trick Room, or Icy Wind support.")

    # Coverage insights
    missing_types = [t for t in type_moves if coverage[t] == 0]
    key_coverages = ", ".join([t for t, c in coverage.items() if c > 0])
    report.append(f"\n**Type Coverage:** Present: {key_coverages or 'None detected'}")

    if len(missing_types) > 5:
        report.append("Coverage appears narrow — could struggle with certain threats.")
    elif "Ground" not in coverage:
        report.append("No Ground coverage — may struggle vs. Heatran or Iron Hands.")
    elif "Ice" not in coverage:
        report.append("No Ice coverage — could struggle with Dragon or Landorus threats.")

    # Roles
    report.append(f"\n**Role Breakdown:** Support: {role_counts['Support']} | Setup: {role_counts['Setup']} | Utility: {role_counts['Utility']}")
    if role_counts["Support"] >= 2 and "Trick Room" in speed_control:
        report.append("Excellent support core — consistent Trick Room setup likely.")
    elif role_counts["Support"] < 1:
        report.append("Lack of reliable redirection or Fake Out could weaken control options.")

    # Smart Suggestions
    suggestions = []
    if "Trick Room" in speed_control and "Tailwind" not in speed_control:
        suggestions.append("Add a faster mode or secondary speed control for versatility outside Trick Room.")
    if "Tailwind" in speed_control and "Trick Room" not in speed_control:
        suggestions.append("Add anti-TR options like Imprison or Taunt to avoid mirror weaknesses.")
    if "Landorus" in " ".join(team) and "Ice" not in coverage:
        suggestions.append("Consider Ice coverage for opposing Landorus mirrors.")
    if "Incineroar" not in " ".join(team) and "Fake Out" not in move_text:
        suggestions.append("Include Fake Out pressure to improve positioning control.")
    if not suggestions:
        suggestions.append("Team appears well-rounded — only fine-tuning may be needed.")

    report.append("\n**Suggested Improvements:**")
    for s in suggestions:
        report.append(f"- {s}")

    return "\n".join(report)


# --- Dynamic recommendation function ---
def recommend_optimizations(team, synergy_report):
    """Recommend improvements dynamically based on missing roles and weaknesses."""
    recs = []

    if not synergy_report["speed_control"]:
        recs.append("Add a form of speed control such as Trick Room, Tailwind, or Icy Wind.")
    if "Lacks redirection" in " ".join(synergy_report["weaknesses"]):
        recs.append("Consider a redirection Pokémon such as Amoonguss or Indeedee.")
    if "Ground" in " ".join(synergy_report["weaknesses"]):
        recs.append("Add a Ground immunity or resist like Landorus-T or Gholdengo.")
    if "Fairy coverage" in " ".join(synergy_report["weaknesses"]):
        recs.append("Include Fairy moves or Pokémon like Iron Valiant or Flutter Mane.")
    if any("Illegal" in w for w in synergy_report["weaknesses"]):
        recs.append("Replace banned Pokémon with legal alternatives for the current Regulation.")

    if not recs:
        recs.append("Team roles appear well covered for this format.")

    return recs

async def handle_team_evaluation(team_text: str, user_id: str):
    """Evaluates and optimizes a given VGC team in Pokepaste format or from a Pokepaste URL."""

    # --- Step 1: If it's a Pokepaste link, fetch the text ---
    if "pokepast.es" in team_text:
        try:
            paste_id = team_text.strip().split("/")[-1]
            url = f"https://pokepast.es/{paste_id}/raw"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                team_text = response.text
            else:
                return {"status": "error", "message": f"Could not retrieve Pokepaste (HTTP {response.status_code})."}
        except Exception as e:
            return {"status": "error", "message": f"Error fetching Pokepaste: {str(e)}"}

    # --- Step 2: Parse team text ---
    teams = parse_pokepaste(team_text)
    if not teams:
        return {"status": "error", "message": "No valid Pokémon sets found. Make sure to paste a full team in Pokepaste format."}
    if len(teams) < 6:
        note = f"⚠️ Only {len(teams)} Pokémon detected — default sets will be filled for missing slots."
        print(note)

    # --- Step 3: Evaluate team synergy ---
    synergy_report = evaluate_synergy(teams)

    # --- Step 4: Create embed ---
    embed = discord.Embed(title="Professor Sequoia — Team Evaluation", color=0x3498db)
    embed.add_field(name="Team Summary", value=synergy_report['summary'], inline=False)
    embed.add_field(name="Weaknesses", value="\n".join(synergy_report['weaknesses']), inline=False)
    # --- Optional: list team members ---
    names = ", ".join([p['name'] for p in teams])
    embed.add_field(name="Team Members", value=names, inline=False)

    embed.set_footer(text="Pokémon VGC Team Evaluation — Professor Sequoia")

    return {"status": "ok", "embed": embed}

async def handle_strategy_request(self, prompt: str, user_id: int):
    """
    Handle Use Case 03 - Matchup and Strategy Advice
    """
    from cogs.strategy import StrategyEngine
    from core.nlp import NLPService
    
    nlp = NLPService()
    intent = nlp.detect_strategy_intent(prompt)
    focus_target = nlp.extract_focus_target(prompt)  # e.g. "Calyrex-Shadow", "Dondozo-Tatsugiri"

    # 1. Try to extract paste from user message
    paste_url = nlp.extract_pokepaste(prompt)

    if paste_url:
        raw_text = self.parser.fetch_pokepaste(paste_url)
        team_data = self.parser.parse_pokepaste(raw_text)
    else:
        # Load user’s last known team (optional feature)
        team_data = self.user_team_cache.get(user_id, None)

    # 2. If still no team → fallback to generic advice
    if not team_data:
        engine = StrategyEngine(self.repo)
        strategy = engine.generic_strategy(focus_target)
        return {"status": "ok", "strategy": strategy}

    # 3. Full team-based matchup analysis
    engine = StrategyEngine(self.repo)
    strategy = engine.analyze_strategy(team_data, focus_target)

    return {"status": "ok", "strategy": strategy}