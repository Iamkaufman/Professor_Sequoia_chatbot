# core/strategy.py  (or cogs/strategy.py if you prefer)
from typing import Dict, List, Optional, Any

import bot


class StrategyEngine:
    def __init__(self, repo: Any):
        """
        repo: repository object (your database/repo module) used for lookups if needed.
        """
        self.repo = repo

    # -------------------------
    # 1. GENERIC STRATEGY MODE
    # -------------------------
    def generic_strategy(self, target: Optional[str] = None) -> Dict[str, Any]:
        if not target:
            return {
                "mode": "generic",
                "advice": [
                    "Without a team provided, here are universal principles:",
                    "• Identify opponent's primary win condition",
                    "• Pressure their support Pokémon first",
                    "• Use Tera defensively unless a KO is guaranteed",
                ],
            }

        target_lower = target.lower()
        if "dondozo" in target_lower and "tatsugiri" in target_lower:
            return {
                "mode": "generic-archetype",
                "archetype": "Dondozo-Tatsugiri",
                "advice": [
                    "Bring Unaware or Clear Smog users where possible.",
                    "Use strong single-target special attackers.",
                    "Keep your Tera for breaking +2 Defense Dondozo or to secure KOs.",
                    "Avoid setting up near Dondozo's soaking support unless you can punish it.",
                ],
            }

        return {
            "mode": "generic",
            "advice": [f"No team provided. General strategy vs {target}: apply pressure early, preserve Tera defensively."],
        }

    # -------------------------
    # 2. TEAM-BASED STRATEGY MODE
    # -------------------------
    def analyze_strategy(self, team_data: List[Dict[str, Any]], target: Optional[str] = None) -> Dict[str, Any]:
        roles = self.identify_roles(team_data)
        leads = self.recommend_leads(team_data, roles)
        tera_notes = self.recommend_tera(team_data, roles)
        wincons = self.identify_win_conditions(team_data)

        matchup = self.matchup_specific(team_data, target) if target else None

        return {
            "mode": "team",
            "roles": roles,
            "recommended_leads": leads,
            "tera_notes": tera_notes,
            "win_conditions": wincons,
            "matchup_specific": matchup,
        }

    # -------------------------
    # COMPONENTS
    # -------------------------
    def identify_roles(self, team: List[Dict[str, Any]]) -> List[tuple]:
        roles: List[tuple] = []
        for p in team:
            name = p.get("name", "Unknown")
            spe = p.get("spe", 0)
            atk = p.get("atk", 0)
            spa = p.get("spa", 0)
            moves = [m.lower() for m in p.get("moves", [])]
            bulk = p.get("hp", 0) + p.get("def", 0) + p.get("spd", 0)

            # Check for Trick Room move first (explicit intent)
            if any(m in moves for m in ("trick room", "trick-room")):
                roles.append((name, "Speed Control / Trick Room"))
            # Check for high offensive stats (win conditions) - before checking bulk
            elif atk >= 130 or spa >= 130:
                roles.append((name, "Primary Win Condition"))
            # Extremely slow Pokemon (spe <= 25) are Trick Room attackers - BEFORE bulk check
            elif spe <= 25:
                roles.append((name, "Speed Control / Trick Room"))
            # Check for bulky pivots (catches moderately slow bulky mons)
            elif bulk >= 250:
                roles.append((name, "Bulky Pivot"))
            # Check for fast attackers
            elif spe >= 100:
                roles.append((name, "Fast Attacker"))
            # Remaining slow Pokemon (26-50)
            elif spe <= 50:
                roles.append((name, "Speed Control / Trick Room"))
            else:
                roles.append((name, "General Attacker"))
        return roles

    def recommend_leads(self, team: List[Dict[str, Any]], roles: List[tuple]) -> List[Any]:
        # simple heuristics: prefer a Fake Out + redirection pair, else fast + bulky
        fake_out_users = [p.get("name") for p in team if any(m.lower() == "fake-out" for m in p.get("moves", []))]
        redirectors = [p.get("name") for p in team if any(m.lower() in ("follow-me", "rage-powder") for m in p.get("moves", []))]

        leads: List[Any] = []
        if fake_out_users and redirectors:
            leads.append({"pair": (fake_out_users[0], redirectors[0]), "reason": "Fake Out + redirector lead for safe turn 1 plays"})

        # fallback pairing: fast + bulky
        fast = next((r[0] for r in roles if r[1] == "Fast Attacker"), None)
        bulky = next((r[0] for r in roles if r[1] == "Bulky Pivot"), None)
        if fast and bulky:
            leads.append({"pair": (fast, bulky), "reason": "Fast attacker + bulky pivot pairing"})

        if not leads:
            leads.append({"pair": None, "reason": "No obvious lead pair identified; consider a lead that maximizes momentum or denies opponent wincons."})

        return leads

    def recommend_tera(self, team: List[Dict[str, Any]], roles: List[tuple]) -> List[str]:
        tera_notes: List[str] = []
        for p in team:
            module = p.get("module", {}) or {}
            tera_type = module.get("tera_type") or p.get("tera_type")
            if tera_type:
                tera_notes.append(f"{p.get('name', 'Unknown')} often Teras {tera_type} to secure KOs or cover weaknesses.")
        return tera_notes

    def identify_win_conditions(self, team: List[Dict[str, Any]]) -> List[str]:
        wincons: List[str] = []
        for p in team:
            if p.get("atk", 0) >= 130:
                wincons.append(f"{p.get('name')} as physical win condition")
            if p.get("spa", 0) >= 130:
                wincons.append(f"{p.get('name')} as special win condition")
        return wincons

    def matchup_specific(self, team: List[Dict[str, Any]], target: Optional[str]) -> List[str]:
        if not target:
            return []

        t = target.lower()
        notes: List[str] = []
        if "calyrex" in t or "shadow" in t:
            notes.append("Preserve Dark-types and pressure Trick Room denial early.")
            notes.append("Avoid leading fastest Pokémon into Shadow Rider without speed control.")
        if "dondozo" in t and "tatsugiri" in t:
            notes.append("Consider Unaware/Clarify users; avoid self-sabotaging setup vs Dondozo soak.")
        if "iron" in t and "hands" in t:
            notes.append("Use Ground or Fairy coverage; Iron Hands is extremely powerful physically—prioritize resistances and pivots.")

        if not notes:
            notes.append("No specific matchup rules recognized; focus on lead choice, momentum, and preserving win conditions.")

        return notes

# simple local test
if __name__ == "__main__":
    engine = StrategyEngine(repo=None)
    sample_team = [
        {"name": "Incineroar", "spe": 60, "moves": ["Fake-Out", "Flare Blitz"], "atk": 115, "spa": 60, "hp": 95, "def": 90, "spd": 90},
        {"name": "Flutter Mane", "spe": 135, "moves": ["Moonblast", "Shadow Ball"], "atk": 55, "spa": 135, "hp": 55, "def": 55, "spd": 135, "module": {"tera_type": "Fairy"}},
    ]
    print(engine.analyze_strategy(sample_team, target="Calyrex-Shadow"))

    
    