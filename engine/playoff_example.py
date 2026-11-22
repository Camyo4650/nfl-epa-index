"""
Example usage of the playoff probability module with the engine.

WARNING: This example uses an empty schedule and an unvalidated prototype.
Its playoff odds and clinching decisions are not reliable.

This demonstrates how to:
1. Load season data from the engine
2. Run Monte Carlo simulations to get playoff odds
3. Use deterministic analysis to find locked/eliminated teams
4. Generate a playoff probability report
"""

import json
from playoff_probability import (
    MonteCarloSimulator, DeterministicPlayoffAnalyzer,
    extract_records_at_week, extract_epa_ratings,
    calculate_remaining_schedule
)


def generate_playoff_report(season_data: dict, current_week: int) -> dict:
    """
    Generate a comprehensive playoff probability report for a season at a given week.
    
    Args:
        season_data: Season data dict from engine.build_season()
        current_week: Current week of the season
        
    Returns:
        Dict with playoff odds, deterministic status, and detailed analysis
    """
    
    # Extract current team records and EPA ratings
    records = extract_records_at_week(season_data, current_week)
    epa_ratings = extract_epa_ratings(season_data, current_week)
    
    if not records:
        return {"error": f"No data available for week {current_week}"}
    
    # Get all games for the season
    all_games = []
    for game_data in season_data.get("gameDetails", []):
        all_games.append(game_data)
    
    # Calculate remaining schedule (this is a simplified version;
    # in production you'd load full schedule from nflreadpy)
    remaining_schedule = []
    
    # Create report
    report = {
        "week": current_week,
        "timestamp": season_data.get("timestamp"),
        "teams": {}
    }
    
    # Run Monte Carlo simulations
    mc_simulator = MonteCarloSimulator(num_simulations=10000)
    playoff_odds = mc_simulator.calculate_playoff_odds(
        records, remaining_schedule, epa_ratings
    )
    
    # Run deterministic analysis
    deterministic_analyzer = DeterministicPlayoffAnalyzer()
    games_remaining = {team_id: 18 - current_week for team_id in records}
    deterministic_status = deterministic_analyzer.analyze_playoff_status(
        records, games_remaining
    )
    
    # Build detailed team report
    for team_id, record in records.items():
        team_report = {
            "record": {
                "wins": record.wins,
                "losses": record.losses,
                "ties": record.ties,
            },
            "conference": record.conference,
            "division": record.division,
            "epa_rating": epa_ratings.get(team_id, 0.0),
            "playoff_probability": playoff_odds.get(team_id, 0.0),
            "playoff_status": deterministic_status.get(team_id, "unknown"),
            "games_remaining": games_remaining.get(team_id, 0),
        }
        report["teams"][team_id] = team_report
    
    # Sort teams by conference and playoff probability
    report["by_conference"] = {}
    for conference in {"AFC", "NFC"}:
        conf_teams = [
            (team_id, data) for team_id, data in report["teams"].items()
            if data["conference"] == conference
        ]
        # Sort by playoff probability (descending)
        conf_teams.sort(
            key=lambda x: (-x[1]["playoff_probability"], x[0])
        )
        report["by_conference"][conference] = [
            {"team_id": team_id, **data} for team_id, data in conf_teams
        ]
    
    # Summary stats
    report["summary"] = {
        "afc": {
            "playoff_locks": sum(
                1 for t in report["by_conference"]["AFC"]
                if t["playoff_status"] == "locked_in"
            ),
            "playoff_eliminations": sum(
                1 for t in report["by_conference"]["AFC"]
                if t["playoff_status"] == "eliminated"
            ),
        },
        "nfc": {
            "playoff_locks": sum(
                1 for t in report["by_conference"]["NFC"]
                if t["playoff_status"] == "locked_in"
            ),
            "playoff_eliminations": sum(
                1 for t in report["by_conference"]["NFC"]
                if t["playoff_status"] == "eliminated"
            ),
        }
    }
    
    return report


def print_playoff_report(report: dict) -> None:
    """Pretty-print a playoff probability report."""
    
    if "error" in report:
        print(f"Error: {report['error']}")
        return
    
    print(f"\n{'='*80}")
    print(f"PLAYOFF PROBABILITY REPORT - Week {report['week']}")
    print(f"{'='*80}\n")
    
    for conference in ["AFC", "NFC"]:
        print(f"\n{conference} TEAMS")
        print(f"{'-'*80}")
        teams = report["by_conference"][conference]
        
        for i, team in enumerate(teams, 1):
            status_symbol = {
                "locked_in": "✓",
                "eliminated": "✗",
                "contention": "→"
            }.get(team["playoff_status"], "?")
            
            print(
                f"{i:2}. {team['team_id']:4} {status_symbol} "
                f"{team['record']['wins']:2}-{team['record']['losses']:2}-{team['record']['ties']:1}  "
                f"EPA: {team['epa_rating']:6.2f}  "
                f"Playoff Odds: {team['playoff_probability']*100:5.1f}%"
            )
    
    print(f"\n{'-'*80}")
    print("SUMMARY")
    print(f"{'-'*80}")
    print(f"AFC Playoff Locks: {report['summary']['afc']['playoff_locks']}")
    print(f"AFC Playoff Eliminations: {report['summary']['afc']['playoff_eliminations']}")
    print(f"NFC Playoff Locks: {report['summary']['nfc']['playoff_locks']}")
    print(f"NFC Playoff Eliminations: {report['summary']['nfc']['playoff_eliminations']}")


if __name__ == "__main__":
    # Example: Load a season and generate report
    # In practice, this would load real data from the engine
    
    # Import the engine module to load data
    try:
        import store
        
        season_data = store.season_data(2024)
        
        # Generate report for week 15
        report = generate_playoff_report(season_data, current_week=15)
        print_playoff_report(report)
        
        # Output JSON for API consumption
        print("\n\nJSON Output:")
        print(json.dumps(report, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo use this example, run it from the engine directory with:")
        print("  python playoff_example.py")
