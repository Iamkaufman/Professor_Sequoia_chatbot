import re
from typing import Dict, List, Optional

# Very small rule-based parser for "build team around X and Y" commands
def parse_buildcore_message(message: str) -> Dict:
    """
    Returns dict:
      {
        'intent': 'build_core',
        'pokemons': ['charizard', 'rotom-wash'],
        'playstyle': 'hyper-offense' or None,
        'regulation': 'reg-h' or None
      }
    """
    text = message.strip()
    res = {'intent': None, 'pokemons': [], 'playstyle': None, 'regulation': None}

    # normalize separators
    text_l = text.lower()

    # intent detection
    if any(k in text_l for k in ["build a team", "build team", "team around", "make a team"]):
        res['intent'] = 'build_core'

    # extract regulation tag (common in messages)
    m_reg = re.search(r"(regulation\s*[a-z0-9-]+|reg-?[a-z0-9]+|regulation\s*\w+)", text_l)
    if m_reg:
        res['regulation'] = m_reg.group(0)

    # search for playstyle keywords
    for style in ['hyper-offense', 'hyper offense', 'balance', 'stall', 'tailwind', 'sun','rain','trick room','fast','sweeper','bulky']:
        if style in text_l:
            res['playstyle'] = style.replace(' ', '-')
            break

    # extract pokemon names by heuristics: look for capitalized words in original or hyphenated tokens
    # recommended: rely on repository search in controller to match names
    # Here we attempt a simple extraction for tokens like "Garchomp", "Rotom-Wash", "Charizard"
    # capture words with uppercase letter or hyphenated tokens
    tokens = re.findall(r"[A-Z][a-z]+(?:-[A-Z][a-z]+)?", message)
    if tokens:
        res['pokemons'] = [t.replace(' ', '-') for t in tokens]

    # fallback: if user provided lower-case names with hyphens (rotom-wash)
    lower_matches = re.findall(r"\b([a-z0-9]+-[a-z0-9]+)\b", text_l)
    for t in lower_matches:
        if t not in res['pokemons']:
            res['pokemons'].append(t)

    return res

def needs_clarification(parsed: Dict) -> bool:
    """Return True if we lack minimal info."""
    return not parsed.get('pokemons')