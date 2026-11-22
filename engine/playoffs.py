"""Provisional playoff picture based on record and a historical EPA model."""

import math
from collections import Counter

from playoff_probability import DeterministicPlayoffAnalyzer, MonteCarloSimulator, extract_records_at_week
from playoff_standings import Standings


def postseason_qualifiers(schedules, season, records):
    wildcard = [game for game in schedules if game["season"] == season and game["game_type"] == "WC"]
    divisional = [game for game in schedules if game["season"] == season and game["game_type"] == "DIV"]
    if len(wildcard) != 6 or len(divisional) != 4:
        return None
    wc_teams = {game[side] for game in wildcard for side in ("home_team", "away_team")}
    div_teams = {game[side] for game in divisional for side in ("home_team", "away_team")}
    byes = div_teams - wc_teams
    qualifiers = wc_teams | byes
    leaders = {game["home_team"] for game in wildcard} | byes
    if (len(wc_teams) != 12 or len(div_teams) != 8 or len(byes) != 2
            or len(qualifiers) != 14 or len(leaders) != 8
            or not qualifiers <= records.keys()):
        raise ValueError("Invalid postseason bracket in schedule.")
    for conference in ("AFC", "NFC"):
        conf_qualifiers = {team for team in qualifiers if records[team].conference == conference}
        conf_leaders = {team for team in leaders if records[team].conference == conference}
        if (len(conf_qualifiers) != 7 or len(conf_leaders) != 4
                or len({records[team].division for team in conf_leaders}) != 4):
            raise ValueError(f"Invalid {conference} postseason bracket in schedule.")
    return qualifiers, leaders


def build_playoff_picture(season_data, schedules, week, simulations=10000, progress=None):
    season = season_data["season"]
    if str(week) not in season_data["weeks"]:
        raise ValueError(f"No completed ranking snapshot for {season} week {week}.")
    rows = season_data["weeks"][str(week)]["combined"]
    teams = {row["id"]: row for row in rows}
    records = extract_records_at_week(season_data, week)
    if len(teams) != 32 or set(teams) != set(records):
        raise ValueError("A complete set of 32 team records and EPA ratings is required.")
    if any(not isinstance(team["epa"], (float, int)) or not math.isfinite(team["epa"])
           for team in teams.values()):
        raise ValueError("A finite EPA rating is required for every team.")
    if simulations < 1:
        raise ValueError("Simulation count must be positive.")
    games = [game for game in schedules if game["season"] == season and game["game_type"] == "REG"]
    counts = Counter(team for game in games for team in (game["home_team"], game["away_team"]))
    expected_games = {
        team: 16 if season == 2020 or (season == 2022 and team in ("BUF", "CIN")) else 17
        for team in records
    }
    if set(counts) != set(records) or any(counts[team] != expected_games[team] for team in records):
        raise ValueError("The complete regular-season schedule is unavailable.")
    schedule = [(game["home_team"], game["away_team"]) for game in games if game["week"] > week]
    history = []
    for game in games:
        if game["week"] <= week:
            home_score, away_score = game["home_score"], game["away_score"]
            if home_score is None or away_score is None:
                raise ValueError(f"Missing completed game score in week {game['week']}.")
            history.append((game["home_team"], game["away_team"],
                            2 if home_score > away_score else 0 if home_score < away_score else 1))
    remaining = Counter(team for game in schedule for team in game)
    for team_id, record in records.items():
        if record.games_played + remaining[team_id] != expected_games[team_id]:
            raise ValueError(f"The schedule does not match the week {week} record for {team_id}.")
    postseason = postseason_qualifiers(schedules, season, records) if not schedule else None
    if postseason:
        qualifiers, leaders = postseason
        statuses = {team: "locked_in" if team in qualifiers else "eliminated" for team in records}
        odds = {team: float(team in qualifiers) for team in records}
    else:
        statuses = DeterministicPlayoffAnalyzer().analyze_playoff_status(
            records, {team_id: remaining[team_id] for team_id in records})
        simulator = MonteCarloSimulator(simulations)
        odds = simulator.calculate_playoff_odds(
            records, schedule, {team_id: team["epa"] for team_id, team in teams.items()},
            game_history=history, progress=progress)
    standings = Standings(records, history)
    conferences = {}
    for conference in ("AFC", "NFC"):
        order, division_winners = standings.conference_picture(conference)
        if postseason:
            division_winners = {team for team in leaders if records[team].conference == conference}
            order = ([team for team in order if team in division_winners]
                     + [team for team in order if team in qualifiers and team not in division_winners]
                     + [team for team in order if team not in qualifiers])
        conferences[conference] = [
            {**{key: teams[team_id].get(key) for key in ("id", "name", "conference", "division", "color", "logo", "record")},
             "rank": rank, "divisionLeader": team_id in division_winners,
             "probability": odds[team_id], "status": statuses[team_id]}
            for rank, team_id in enumerate(order, 1)
        ]
    return {"season": season, "week": week, "simulations": 0 if postseason else simulations,
            "statusSource": "postseason" if postseason else "record_bounds", "conferences": conferences}
