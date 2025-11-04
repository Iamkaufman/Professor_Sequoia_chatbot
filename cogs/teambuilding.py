"""
Professor Sequoia - Teambuilding Logic
Helper functions for building teams around cores
"""
import sys
import os
# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import PokemonDatabase
from typing import List, Dict, Optional, Tuple


class TeamBuilder:
    """Helper class for VGC teambuilding analysis"""
    
    def __init__(self, db: PokemonDatabase):
        self.db = db
    
    def analyze_core(self, core_pokemon: List[str], format_filter: str = "reg-h") -> Dict:
        """
        Comprehensive analysis of a Pokemon core
        
        Args:
            core_pokemon: List of 2-3 Pokemon names forming the core
            format_filter: VGC format to check
        
        Returns:
            Dictionary with comprehensive core analysis
        """
        # Get Pokemon data
        pokemon_data = []
        for name in core_pokemon:
            data = self.db.get_pokemon(name, format_filter)
            if not data:
                return {'error': f'Pokemon {name} not found or not legal in {format_filter}'}
            pokemon_data.append(data)
        
        # Analyze defensive typing
        team_type_analysis = self.db.analyze_team_types(core_pokemon)
        
        # Analyze offensive coverage
        offensive_coverage = self._analyze_offensive_coverage(pokemon_data)
        
        # Speed tier analysis
        speed_analysis = self._analyze_speed_tiers(pokemon_data)
        
        # Identify synergies
        synergies = self._identify_synergies(pokemon_data)
        
        # Identify what the core needs
        recommendations = self._generate_recommendations(
            pokemon_data,
            team_type_analysis,
            offensive_coverage,
            speed_analysis
        )
        
        return {
            'core_pokemon': [p['name'] for p in pokemon_data],
            'defensive_analysis': team_type_analysis,
            'offensive_coverage': offensive_coverage,
            'speed_analysis': speed_analysis,
            'synergies': synergies,
            'recommendations': recommendations
        }
    
    def _analyze_offensive_coverage(self, pokemon_data: List[Dict]) -> Dict:
        """Analyze what types the core can hit effectively"""
        all_move_types = set()
        
        for pkmn in pokemon_data:
            # Add STAB types
            all_move_types.add(pkmn['type1'])
            if pkmn['type2']:
                all_move_types.add(pkmn['type2'])
            
            # Get actual moves if available
            moves = self.db.get_pokemon_moves(pkmn['name'])
            for move in moves:
                all_move_types.add(move['type'])
        
        # Calculate coverage
        coverage = self.db.calculate_offensive_coverage(list(all_move_types))
        
        return {
            'move_types_available': list(all_move_types),
            'super_effective_against': coverage['super_effective'],
            'resisted_by': coverage['resisted'],
            'immune_types': coverage['immune'],
            'coverage_score': len(coverage['super_effective']) + len(coverage['neutral'])
        }
    
    def _analyze_speed_tiers(self, pokemon_data: List[Dict]) -> Dict:
        """Analyze speed characteristics of the core"""
        speeds = [(p['name'], p['spe']) for p in pokemon_data]
        speeds_sorted = sorted(speeds, key=lambda x: x[1], reverse=True)
        
        avg_speed = sum(s for _, s in speeds) / len(speeds)
        
        # Categorize speed
        if avg_speed >= 100:
            speed_category = "fast"
        elif avg_speed >= 70:
            speed_category = "medium"
        else:
            speed_category = "slow"
        
        return {
            'speeds': speeds_sorted,
            'average_speed': avg_speed,
            'speed_category': speed_category,
            'fastest': speeds_sorted[0],
            'slowest': speeds_sorted[-1]
        }
    
    def _identify_synergies(self, pokemon_data: List[Dict]) -> List[str]:
        """Identify positive synergies between core Pokemon"""
        synergies = []
        
        # Check for Intimidate + physical attackers
        intimidate_users = [p['name'] for p in pokemon_data 
                           if 'intimidate' in str(p.get('ability1_name', '')).lower() or
                              'intimidate' in str(p.get('ability2_name', '')).lower() or
                              'intimidate' in str(p.get('ability3_name', '')).lower()]
        
        physical_attackers = [p['name'] for p in pokemon_data if p['atk'] > p['spa']]
        
        if intimidate_users:
            synergies.append(f"Intimidate support from {', '.join(intimidate_users)} helps physical bulk")
        
        # Check for complementary typing
        all_types = set()
        for p in pokemon_data:
            all_types.add(p['type1'])
            if p['type2']:
                all_types.add(p['type2'])
        
        if len(all_types) >= 4:
            synergies.append("Good type diversity provides flexible matchup options")
        
        # Check for weather setters
        weather_abilities = ['drought', 'drizzle', 'sand-stream', 'snow-warning']
        weather_users = []
        for p in pokemon_data:
            for ability_key in ['ability1_name', 'ability2_name', 'ability3_name']:
                ability = p.get(ability_key, '')
                if ability and ability.lower() in weather_abilities:
                    weather_users.append((p['name'], ability))
        
        if weather_users:
            for name, ability in weather_users:
                synergies.append(f"{name}'s {ability} can enable weather strategies")
        
        # Check for terrain setters
        terrain_abilities = ['electric-surge', 'grassy-surge', 'psychic-surge', 'misty-surge']
        terrain_users = []
        for p in pokemon_data:
            for ability_key in ['ability1_name', 'ability2_name', 'ability3_name']:
                ability = p.get(ability_key, '')
                if ability and ability.lower() in terrain_abilities:
                    terrain_users.append((p['name'], ability))
        
        if terrain_users:
            for name, ability in terrain_users:
                synergies.append(f"{name}'s {ability} can enable terrain strategies")
        
        return synergies
    
    def _generate_recommendations(self, pokemon_data: List[Dict], 
                                  type_analysis: Dict,
                                  offensive_coverage: Dict,
                                  speed_analysis: Dict) -> Dict:
        """Generate recommendations for completing the team"""
        recommendations = {
            'defensive_needs': [],
            'offensive_needs': [],
            'speed_control': [],
            'support_options': [],
            'specific_counters': []
        }
        
        # Defensive needs based on major weaknesses
        major_weaknesses = type_analysis.get('major_weaknesses', [])
        if major_weaknesses:
            recommendations['defensive_needs'].append(
                f"Team is weak to: {', '.join(major_weaknesses)}. "
                f"Consider adding Pokemon that resist these types."
            )
            
            # Suggest types that resist major weaknesses
            resistant_types = self._find_resistant_types(major_weaknesses)
            if resistant_types:
                recommendations['defensive_needs'].append(
                    f"Suggested types to cover weaknesses: {', '.join(resistant_types)}"
                )
        
        # Offensive coverage gaps
        immune_types = offensive_coverage.get('immune_types', [])
        resisted_types = offensive_coverage.get('resisted_by', [])
        
        if immune_types:
            recommendations['offensive_needs'].append(
                f"Cannot hit: {', '.join(immune_types)}. Add coverage moves or Pokemon."
            )
        
        if len(resisted_types) > 6:
            recommendations['offensive_needs'].append(
                f"Coverage is resisted by many types. Consider adding diverse attacking types."
            )
        
        # Speed control recommendations
        speed_cat = speed_analysis['speed_category']
        
        if speed_cat == "slow":
            recommendations['speed_control'].append(
                "Core is slow. Consider Trick Room support or priority moves."
            )
        elif speed_cat == "medium":
            recommendations['speed_control'].append(
                "Mixed speed tier. Tailwind or Trick Room could both work depending on matchup."
            )
        else:
            recommendations['speed_control'].append(
                "Fast core. Consider Tailwind to outspeed other fast teams."
            )
        
        # Support options
        has_fake_out = False
        has_redirector = False
        
        for pkmn in pokemon_data:
            moves = self.db.get_pokemon_moves(pkmn['name'])
            move_names = [m['name'] for m in moves]
            
            if 'fake-out' in move_names:
                has_fake_out = True
            if 'follow-me' in move_names or 'rage-powder' in move_names:
                has_redirector = True
        
        if not has_fake_out:
            recommendations['support_options'].append(
                "No Fake Out user. Consider adding Fake Out for turn 1 pressure."
            )
        
        if not has_redirector:
            recommendations['support_options'].append(
                "No redirection. Consider Follow Me/Rage Powder users to protect setup sweepers."
            )
        
        # Check for setup sweepers
        high_attack_pokemon = [p for p in pokemon_data if p['atk'] >= 130 or p['spa'] >= 130]
        if high_attack_pokemon:
            recommendations['support_options'].append(
                "Core has strong attackers. Screens, Helping Hand, or stat boosting could be valuable."
            )
        
        return recommendations
    
    def _find_resistant_types(self, weak_types: List[str]) -> List[str]:
        """Find types that resist the given weak types"""
        all_types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice', 
                     'fighting', 'poison', 'ground', 'flying', 'psychic', 
                     'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
        
        resistant_types = []
        
        for potential_type in all_types:
            resists_count = 0
            for weak_type in weak_types:
                effectiveness = self.db.get_type_effectiveness(weak_type, potential_type)
                if effectiveness < 1.0:
                    resists_count += 1
            
            # If it resists at least half of the weaknesses
            if resists_count >= len(weak_types) / 2:
                resistant_types.append(potential_type)
        
        return resistant_types[:5]  # Return top 5
    
    def suggest_teammates(self, core_pokemon: List[str], 
                         format_filter: str = "reg-h",
                         num_suggestions: int = 10) -> List[Dict]:
        """
        Suggest Pokemon that would complement the core
        
        Args:
            core_pokemon: List of Pokemon names in the core
            format_filter: VGC format
            num_suggestions: Number of suggestions to return
        
        Returns:
            List of suggested Pokemon with reasoning
        """
        # Get core analysis
        analysis = self.analyze_core(core_pokemon, format_filter)
        
        if 'error' in analysis:
            return []
        
        suggestions = []
        
        # Get major weaknesses to cover
        major_weaknesses = analysis['defensive_analysis'].get('major_weaknesses', [])
        
        # Get missing offensive types
        resisted_types = analysis['offensive_coverage'].get('resisted_by', [])
        immune_types = analysis['offensive_coverage'].get('immune_types', [])
        
        # Search for Pokemon that help with these issues
        # This is a simplified version - you'd want more sophisticated logic
        
        # Example: Find Pokemon with types that resist major weaknesses
        for weak_type in major_weaknesses[:3]:  # Top 3 weaknesses
            # Find types that resist this
            all_types = ['steel', 'water', 'fire', 'grass', 'electric', 'fairy', 'dragon']
            for pkmn_type in all_types:
                effectiveness = self.db.get_type_effectiveness(weak_type, pkmn_type)
                if effectiveness < 1.0:
                    # Find Pokemon of this type
                    candidates = self.db.search_pokemon_by_type(pkmn_type, format_filter=format_filter)
                    for candidate in candidates[:2]:  # Top 2 of each type
                        if candidate['name'] not in core_pokemon:
                            suggestions.append({
                                'pokemon': candidate['name'],
                                'reason': f"Resists {weak_type}-type attacks ({effectiveness}x damage)",
                                'stats': {
                                    'hp': candidate['hp'],
                                    'atk': candidate['atk'],
                                    'def': candidate['def'],
                                    'spa': candidate['spa'],
                                    'spd': candidate['spd'],
                                    'spe': candidate['spe']
                                }
                            })
        
        # Remove duplicates and limit results
        seen = set()
        unique_suggestions = []
        for sugg in suggestions:
            if sugg['pokemon'] not in seen:
                seen.add(sugg['pokemon'])
                unique_suggestions.append(sugg)
        
        return unique_suggestions[:num_suggestions]
    
    def format_core_analysis(self, analysis: Dict) -> str:
        """
        Format core analysis into a readable string for Discord
        
        Args:
            analysis: Output from analyze_core()
        
        Returns:
            Formatted string ready for Discord message
        """
        if 'error' in analysis:
            return f"Error: {analysis['error']}"
        
        output = []
        output.append(f"**Core Analysis: {', '.join(analysis['core_pokemon'])}**\n")
        
        # Defensive analysis
        output.append("**Defensive Profile:**")
        major_weak = analysis['defensive_analysis'].get('major_weaknesses', [])
        if major_weak:
            output.append(f"⚠️ Major Weaknesses: {', '.join(major_weak)}")
        else:
            output.append("✅ No major team-wide weaknesses")
        
        good_resist = analysis['defensive_analysis'].get('good_resistances', [])
        if good_resist:
            output.append(f"🛡️ Strong Resistances: {', '.join(good_resist)}")
        
        output.append("")
        
        # Offensive coverage
        output.append("**Offensive Coverage:**")
        coverage_score = analysis['offensive_coverage']['coverage_score']
        output.append(f"Coverage Score: {coverage_score}/18 types")
        
        immune = analysis['offensive_coverage'].get('immune_types', [])
        if immune:
            output.append(f"❌ Cannot hit: {', '.join(immune)}")
        
        output.append("")
        
        # Speed analysis
        output.append("**Speed Profile:**")
        speed_info = analysis['speed_analysis']
        output.append(f"Category: {speed_info['speed_category'].title()}")
        output.append(f"Fastest: {speed_info['fastest'][0]} ({speed_info['fastest'][1]} base speed)")
        output.append(f"Slowest: {speed_info['slowest'][0]} ({speed_info['slowest'][1]} base speed)")
        
        output.append("")
        
        # Synergies
        if analysis['synergies']:
            output.append("**Synergies:**")
            for synergy in analysis['synergies']:
                output.append(f"✨ {synergy}")
            output.append("")
        
        # Recommendations
        output.append("**Recommendations:**")
        recs = analysis['recommendations']
        
        if recs['defensive_needs']:
            output.append("\n*Defensive:*")
            for need in recs['defensive_needs']:
                output.append(f"• {need}")
        
        if recs['offensive_needs']:
            output.append("\n*Offensive:*")
            for need in recs['offensive_needs']:
                output.append(f"• {need}")
        
        if recs['speed_control']:
            output.append("\n*Speed Control:*")
            for need in recs['speed_control']:
                output.append(f"• {need}")
        
        if recs['support_options']:
            output.append("\n*Support:*")
            for need in recs['support_options']:
                output.append(f"• {need}")
        
        return "\n".join(output)


# Example usage for testing
if __name__ == "__main__":
    db = PokemonDatabase()
    builder = TeamBuilder(db)
    
    # Analyze Tyranitar + Excadrill core
    core = ['tyranitar', 'excadrill']
    analysis = builder.analyze_core(core)
    
    print(builder.format_core_analysis(analysis))
    print("\n" + "="*60 + "\n")
    
    # Get teammate suggestions
    suggestions = builder.suggest_teammates(core, num_suggestions=5)
    print("**Suggested Teammates:**")
    for sugg in suggestions:
        print(f"\n{sugg['pokemon'].title()}")
        print(f"  Reason: {sugg['reason']}")