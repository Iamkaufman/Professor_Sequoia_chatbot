import re
import sys
import os
import asyncio
import random
from typing import List, Dict, Any
import importlib

# --- Import dependencies ---
from database.repository import Repository
from core.nlp import parse_buildcore_message, needs_clarification

repo = Repository()


async def handle_buildcore_request(raw_message: str, user_id: str) -> Dict[str, Any]:
    """
    Returns a dict with keys:
      status: 'ok' | 'clarify' | 'error'
      message: text to send the user (or clarifying question)
      team: optional list of dicts describing recommended Pokemon
    """
    parsed = parse_buildcore_message(raw_message)

    # --- Hotfix: fallback if parser failed ---
    if parsed.get('intent') != 'build_core' or not parsed.get('pokemons'):
        # normalize and clean the user text
        text = re.sub(r"[^a-zA-Z0-9\s,\-]", " ", raw_message).lower()

        # fetch known Pokémon names (already lowercase in DB)
        all_names = await repo.get_all_pokemon_names()

        # find known Pokémon names in the message
        matches = [name for name in all_names if name in text]

        print("🧩 Debug — text:", text)
        print("🧩 Debug — matches:", matches)

        if matches:
            parsed['pokemons'] = list(dict.fromkeys(matches))  # deduplicate while preserving order
            parsed['intent'] = 'build_core'
        else:
            # fallback: try to extract words after the command
            parts = text.split("buildcore", 1)
            if len(parts) > 1:
                pokes = [p.strip().capitalize() for p in re.split(r"[,\s]+", parts[1]) if p.strip()]
                parsed['pokemons'] = pokes
                parsed['intent'] = 'build_core'
    # --- End of hotfix ---

    # ✅ now check the result AFTER the fallback
    if parsed.get('intent') != 'build_core':
        return {'status': 'error', 'message': "I couldn't detect a build request in your message."}

    if needs_clarification(parsed):
        return {
            'status': 'clarify',
            'message': (
                "I didn't catch which Pokémon to build around. "
                "Please tell me one or two core Pokémon (e.g., `!buildcore Charizard, Rotom-Wash`)."
            )
        }

    # Try to resolve Pokémon names
    resolved = []
    for p in parsed['pokemons']:
        info = await repo.get_pokemon_by_name(p)
        if info:
            resolved.append(info)
            continue
        candidates = await repo.search_pokemon_by_partial(p, limit=5)
        if len(candidates) == 1:
            resolved.append(candidates[0])
        elif candidates:
            resolved.append(candidates[0])
        else:
            return {'status': 'clarify', 'message': f"I couldn't find `{p}` in my database. Did you mean something else?"}

    # --- Build team ---
    team = []
    core_ids = [p['pokemon_id'] for p in resolved]
    team.extend(resolved)

    # Compute core types
    core_types = set()
    for p in resolved:
        if p.get('type1'):
            core_types.add(p['type1'])
        if p.get('type2'):
            core_types.add(p['type2'])
    core_types.discard(None)

    # Pull candidate pool
    pool = await repo.query_pokemon_pool(exclude_ids=core_ids, limit=500)

    # Simple scoring heuristic
    def score_candidate(cand):
        types = {cand.get('type1'), cand.get('type2')}
        types.discard(None)
        score = 0
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
            'rock': ['fire', 'ice', 'flying', 'bug']
        }
        for t in types:
            for ct in core_types:
                if ct in strength.get(t, []):
                    score += 1
        score += random.random() * 0.1
        return score

    # Sort and select
    scored = sorted(pool, key=score_candidate, reverse=True)
    picks = []
    for cand in scored:
        if len(team) + len(picks) >= 6:
            break
        picks.append(cand)

    team.extend(picks[:max(0, 6 - len(team))])

    # --- Assign moves, items, and EVs ---
    for member in team:
        moves = await repo.get_moves_for_pokemon(member['pokemon_id'])
        moves_sorted = sorted(moves, key=lambda m: (m.get('power') or 0), reverse=True)
        member['suggested_moves'] = [m['name'] for m in moves_sorted[:4]]
        member['suggested_item'] = "Choice Scarf" if member.get('spe', 0) > 90 else "Leftovers"
        member['suggested_ev'] = (
            "252 Atk / 252 Spe / 4 HP"
            if member.get('atk', 0) > member.get('spa', 0)
            else "252 SpA / 252 Spe / 4 HP"
        )

    # --- Build response ---
    response_lines = ["Here’s a team built around your core:"]
    for m in team:
        response_lines.append(
            f"- {m['name'].title()} — Moves: {', '.join(m.get('suggested_moves', []))}; "
            f"Item: {m.get('suggested_item')}; EVs: {m.get('suggested_ev')}"
        )

    return {'status': 'ok', 'message': '\n'.join(response_lines), 'team': team, 'raw_parsed': parsed}
