import argparse
import json
import math
import sys
from collections import defaultdict

import nflreadpy as nfl


MIN_SEASON = 2020


def completed_games(schedules):
    return [
        game for game in schedules.to_dicts()
        if game["game_type"] == "REG"
        and game["home_score"] is not None
        and game["away_score"] is not None
    ]


def available_seasons():
    games = completed_games(nfl.load_schedules(True))
    return sorted({game["season"] for game in games if game["season"] >= MIN_SEASON}, reverse=True)


def add_game_details(result, schedules):
    season = result["season"]
    games = [game for game in schedules if game["season"] == season and game["game_type"] == "REG"]
    by_week = defaultdict(dict)
    last_week = max(map(int, result["weeks"]))
    for game in games:
        week = game["week"]
        if week > last_week:
            continue
        if game["home_score"] is None or game["away_score"] is None:
            raise ValueError(f"Missing score for {season} week {week}.")
        for side, other in (("home", "away"), ("away", "home")):
            team, opponent = game[f"{side}_team"], game[f"{other}_team"]
            if team in by_week[week]:
                raise ValueError(f"Multiple games for {team} in {season} week {week}.")
            by_week[week][team] = {
                "status": "played",
                "opponent": opponent,
                "home": side == "home",
                "teamScore": game[f"{side}_score"],
                "opponentScore": game[f"{other}_score"],
            }

    points = defaultdict(lambda: {"for": 0, "allowed": 0})
    opponents = defaultdict(list)
    last_counted_week = 0
    for week_key, snapshot in sorted(result["weeks"].items(), key=lambda item: int(item[0])):
        week = int(week_key)
        if not by_week[week]:
            raise ValueError(f"No games found for {season} week {week}.")
        for earlier_week in range(last_counted_week + 1, week + 1):
            for team_id, game in by_week[earlier_week].items():
                points[team_id]["for"] += game["teamScore"]
                points[team_id]["allowed"] += game["opponentScore"]
                opponents[team_id].append(game["opponent"])
        offense = {row["id"]: row["epa"] for row in snapshot["offense"]}
        defense = {row["id"]: row["epa"] for row in snapshot["defense"]}
        opponent_rating = {
            team_id: value - defense[team_id]
            for team_id, value in offense.items() if team_id in defense
        }
        sos = {
            team_id: sum(opponent_rating[opponent] for opponent in played) / len(played)
            for team_id, played in opponents.items()
            if played and all(opponent in opponent_rating for opponent in played)
        }
        sos_ranks = {
            team_id: rank for rank, team_id in enumerate(
                sorted(sos, key=lambda team_id: (-sos[team_id], team_id)), 1
            )
        }
        for rows in snapshot.values():
            for team in rows:
                team_points = points[team["id"]]
                team["strengthOfSchedule"] = sos.get(team["id"])
                team["strengthOfScheduleRank"] = sos_ranks.get(team["id"])
                team["points"] = {
                    "for": team_points["for"], "allowed": team_points["allowed"],
                    "net": team_points["for"] - team_points["allowed"],
                }
                team["games"] = {
                    "current": by_week[week].get(team["id"], {"status": "bye"}),
                    "previous": (by_week[week - 1].get(team["id"], {"status": "bye"})
                                 if str(week - 1) in result["weeks"] else {"status": "unavailable"}),
                }
        last_counted_week = week
    result["gameDetailsVersion"] = 4
    return result


def build_season(season, teams, games, plays):
    games = [g for g in games if g["season"] == season]
    games = [g for g in games if g["game_type"] == "REG"]
    play_games = {p["game_id"] for p in plays if p["season_type"] == "REG" and p["epa"] is not None}
    weeks = []
    for week in sorted({g["week"] for g in games}):
        week_games = [g for g in games if g["week"] == week]
        if not all(g["home_score"] is not None and g["away_score"] is not None and g["game_id"] in play_games for g in week_games):
            break
        weeks.append(week)
    if not weeks:
        raise ValueError(f"No complete regular-season weeks with play data for {season}.")

    team_ids = {g[key] for g in games for key in ("home_team", "away_team")}
    team_data = {}
    for row in teams:
        if row["team_abbr"] in team_ids:
            team_data[row["team_abbr"]] = {
                "id": row["team_abbr"],
                "name": row["team_name"],
                "conference": row["team_conf"],
                "division": row["team_division"].split(" ", 1)[-1],
                "color": row["team_color"],
                "secondaryColor": row["team_color2"],
                "logo": row["team_logo_espn"],
            }
    if team_ids != set(team_data):
        raise ValueError(f"Missing team metadata: {sorted(team_ids - set(team_data))}")

    completed_ids = {game["game_id"] for game in games}
    valid_plays = [
        play for play in plays
        if play["season_type"] == "REG"
        and play["game_id"] in completed_ids
        and play["play_type"] in ("pass", "run", "kickoff", "punt", "field_goal", "extra_point")
        and play["epa"] is not None and math.isfinite(play["epa"])
        and play["posteam"] in team_ids and play["defteam"] in team_ids
        and not play["qb_kneel"] and not play["qb_spike"] and not play["play_deleted"]
    ]
    snapshots = {}
    metric_names = ("offense", "defense", "special", "combined")
    previous = {metric: {} for metric in metric_names}
    previous_week = None
    for week in weeks:
        if previous_week != week - 1:
            previous = {metric: {} for metric in metric_names}
        records = {team: {"wins": 0, "losses": 0, "ties": 0} for team in team_ids}
        for game in games:
            if game["week"] > week:
                continue
            home, away = records[game["home_team"]], records[game["away_team"]]
            if game["home_score"] == game["away_score"]:
                home["ties"] += 1
                away["ties"] += 1
            else:
                winner, loser = (home, away) if game["home_score"] > game["away_score"] else (away, home)
                winner["wins"] += 1
                loser["losses"] += 1
        metrics = {name: defaultdict(list) for name in ("offense", "defense", "special")}
        for play in valid_plays:
            if play["week"] <= week:
                if play["play_type"] in ("pass", "run"):
                    metrics["offense"][play["posteam"]].append(play["epa"])
                    metrics["defense"][play["defteam"]].append(play["epa"])
                else:
                    metrics["special"][play["posteam"]].append(play["epa"])
                    metrics["special"][play["defteam"]].append(-play["epa"])
        snapshot = {}
        all_averages = {
            metric: {team: sum(values) / len(values) for team, values in values_by_team.items()}
            for metric, values_by_team in metrics.items()
        }
        all_averages["combined"] = {
            team: all_averages["offense"][team] - all_averages["defense"][team] + all_averages["special"][team]
            for team in team_ids
            if all(team in all_averages[metric] for metric in ("offense", "defense", "special"))
        }
        for metric in metric_names:
            averages = all_averages[metric]
            order = sorted(averages, key=lambda team: ((averages[team] if metric == "defense" else -averages[team]), team))
            ranked = []
            current = {}
            for rank, team in enumerate(order, 1):
                old_rank = previous[metric].get(team)
                ranked.append({
                    **team_data[team], "record": records[team], "rank": rank,
                    "previousRank": old_rank, "change": old_rank - rank if old_rank is not None else None,
                    "epa": averages[team],
                    "plays": None if metric == "combined" else len(metrics[metric][team]),
                })
                current[team] = rank
            previous[metric] = current
            snapshot[metric] = ranked
        snapshots[str(week)] = snapshot
        previous_week = week
    return add_game_details({"season": season, "weeks": snapshots}, games)


def main():
    import store

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seasons", "season", "status", "refresh"])
    parser.add_argument("--season", type=int)
    args = parser.parse_args()
    if args.command == "refresh":
        store.refresh()
        result = store.status()
    elif args.command == "status":
        result = store.status()
    elif args.command == "seasons":
        if store.status()["lastSuccessfulRefresh"] is None:
            store.refresh()
        result = store.seasons()
    else:
        if args.season is None or args.season < MIN_SEASON:
            parser.error(f"season must be at least {MIN_SEASON}")
        result = store.season_data(args.season)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Engine error: {error}", file=sys.stderr)
        sys.exit(1)
