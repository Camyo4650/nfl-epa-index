import unittest

from engine import add_game_details, build_season, completed_games


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.teams = [
            {"team_abbr": "A", "team_name": "Team A", "team_conf": "AFC", "team_division": "AFC East",
             "team_color": "#111111", "team_color2": "#222222", "team_logo_espn": "https://example.com/a.png"},
            {"team_abbr": "B", "team_name": "Team B", "team_conf": "NFC", "team_division": "NFC West",
             "team_color": "#333333", "team_color2": "#444444", "team_logo_espn": "https://example.com/b.png"},
        ]
        self.games = [
            {"game_id": "g1", "season": 2024, "week": 1, "game_type": "REG",
             "home_team": "A", "away_team": "B", "home_score": 7, "away_score": 7},
            {"game_id": "g2", "season": 2024, "week": 2, "game_type": "REG",
             "home_team": "A", "away_team": "B", "home_score": 14, "away_score": 7},
        ]

    def play(self, game_id, week, offense, defense, epa, **overrides):
        return {
            "game_id": game_id, "season_type": "REG", "week": week, "play_type": "pass",
            "posteam": offense, "defteam": defense, "epa": epa, "qb_kneel": 0,
            "qb_spike": 0, "play_deleted": 0, **overrides,
        }

    def test_epa_records_ranks_movement_and_play_exclusions(self):
        plays = [
            self.play("g1", 1, "A", "B", 0.4),
            self.play("g1", 1, "B", "A", -0.2),
            self.play("g2", 2, "A", "B", -0.8),
            self.play("g2", 2, "B", "A", 0.4),
            self.play("g2", 2, "A", "B", 100, qb_kneel=1),
            self.play("g2", 2, "A", "B", 100, qb_spike=1),
            self.play("g2", 2, "A", "B", 100, play_deleted=1),
            self.play("g2", 2, "A", "B", 100, play_type="punt"),
            self.play("g2", 2, "A", "B", None),
            self.play("g2", 2, "A", "B", float("nan")),
            self.play("unfinished", 2, "A", "B", 100),
        ]
        data = build_season(2024, self.teams, self.games, plays)
        first = data["weeks"]["1"]["offense"]
        second = data["weeks"]["2"]["offense"]
        defense = data["weeks"]["2"]["defense"]
        self.assertEqual([team["id"] for team in first], ["A", "B"])
        self.assertEqual([team["id"] for team in second], ["B", "A"])
        self.assertAlmostEqual(second[0]["epa"], 0.1)
        self.assertEqual(second[0]["change"], 1)
        self.assertEqual(second[1]["record"], {"wins": 1, "losses": 0, "ties": 1})
        self.assertEqual(first[0]["points"], {"for": 7, "allowed": 7, "net": 0})
        self.assertEqual(second[1]["points"], {"for": 21, "allowed": 14, "net": 7})
        self.assertEqual(second[0]["points"], {"for": 14, "allowed": 21, "net": -7})
        self.assertEqual({row["id"]: row["points"] for row in defense},
                         {"A": {"for": 21, "allowed": 14, "net": 7},
                          "B": {"for": 14, "allowed": 21, "net": -7}})
        self.assertEqual([team["id"] for team in defense], ["B", "A"])
        self.assertEqual(defense[0]["plays"], 2)
        game = second[0]["games"]
        self.assertEqual(game["current"], {"status": "played", "opponent": "A", "home": False, "teamScore": 7, "opponentScore": 14})
        self.assertEqual(game["previous"]["teamScore"], 7)
        self.assertEqual(first[0]["games"]["previous"], {"status": "unavailable"})

    def test_bye_week_is_reported_for_current_and_previous_week(self):
        games = [self.games[0], {**self.games[1], "home_team": "B", "away_team": "C"}]
        teams = self.teams + [{**self.teams[0], "team_abbr": "C", "team_name": "Team C"}]
        plays = [self.play("g1", 1, "A", "B", 0.2), self.play("g2", 2, "B", "C", 0.1),
                 self.play("g2", 2, "C", "B", -0.1)]
        result = build_season(2024, teams, games, plays)
        teams_by_id = {team["id"]: team for team in result["weeks"]["2"]["offense"]}
        self.assertEqual(teams_by_id["A"]["games"]["current"], {"status": "bye"})
        self.assertEqual(teams_by_id["A"]["points"], {"for": 7, "allowed": 7, "net": 0})
        self.assertEqual(teams_by_id["C"]["games"]["previous"], {"status": "bye"})

    def test_missing_week_does_not_compare_against_earlier_week(self):
        games = [self.games[0], {**self.games[1], "week": 3}]
        plays = [self.play("g1", 1, "A", "B", 0.2), self.play("g2", 3, "B", "A", 0.1)]
        data = build_season(2024, self.teams, games, plays)
        self.assertTrue(all(row["previousRank"] is None for row in data["weeks"]["3"]["offense"]))
        self.assertEqual(data["weeks"]["3"]["offense"][0]["points"], {"for": 21, "allowed": 14, "net": 7})

    def test_special_teams_and_combined_epa(self):
        plays = [
            self.play("g1", 1, "A", "B", 0.4),
            self.play("g1", 1, "B", "A", -0.2),
            self.play("g1", 1, "B", "A", 0.6, play_type="kickoff"),
            self.play("g1", 1, "A", "B", -0.2, play_type="punt"),
        ]
        data = build_season(2024, self.teams, [self.games[0]], plays)["weeks"]["1"]
        special = {row["id"]: row for row in data["special"]}
        combined = {row["id"]: row for row in data["combined"]}
        self.assertAlmostEqual(special["A"]["epa"], -0.4)
        self.assertAlmostEqual(special["B"]["epa"], 0.4)
        self.assertAlmostEqual(combined["A"]["epa"], (0.4 - (-0.2) - 0.8) / 4)
        self.assertAlmostEqual(combined["B"]["epa"], (-0.2 - 0.4 + 0.8) / 4)
        self.assertEqual(data["combined"][0]["id"], "B")
        for metric in data.values():
            row = next(team for team in metric if team["id"] == "A")
            self.assertAlmostEqual(row["strengthOfSchedule"], -0.2 - 0.4)

    def test_combined_weights_all_qualifying_plays_through_each_week(self):
        plays = [
            self.play("g1", 1, "A", "B", 0.8),
            self.play("g1", 1, "A", "B", 0.4),
            self.play("g1", 1, "B", "A", 0.1),
            self.play("g1", 1, "A", "B", 0.2, play_type="punt"),
            self.play("g2", 2, "A", "B", -0.9),
            self.play("g2", 2, "B", "A", 0.8),
            self.play("g2", 2, "B", "A", 0.8),
            self.play("g2", 2, "B", "A", -0.3, play_type="punt"),
            self.play("g2", 2, "A", "B", 100, qb_kneel=1),
            self.play("g2", 2, "A", "B", 100, play_type="punt", play_deleted=1),
        ]
        result = build_season(2024, self.teams, self.games, plays)
        self.assertEqual(result["combinedEpaVersion"], 1)
        first = {row["id"]: row for row in result["weeks"]["1"]["combined"]}
        second = {row["id"]: row for row in result["weeks"]["2"]["combined"]}
        self.assertAlmostEqual(first["A"]["epa"], (0.8 + 0.4 - 0.1 + 0.2) / 4)
        self.assertAlmostEqual(second["A"]["epa"], (0.8 + 0.4 - 0.9 - 0.1 - 0.8 - 0.8 + 0.2 + 0.3) / 8)
        self.assertAlmostEqual(second["B"]["epa"], -second["A"]["epa"])
        self.assertEqual((first["A"]["rank"], second["A"]["rank"], second["A"]["previousRank"], second["A"]["change"]), (1, 2, 1, -1))
        self.assertIsNone(second["A"]["plays"])

    def test_combined_still_requires_each_component(self):
        plays = [self.play("g1", 1, "A", "B", 0.4),
                 self.play("g1", 1, "B", "A", -0.2)]
        result = build_season(2024, self.teams, [self.games[0]], plays)
        self.assertEqual(result["weeks"]["1"]["combined"], [])

    def test_week_not_published_until_all_games_and_play_data_are_complete(self):
        incomplete = {**self.games[1], "game_id": "g3", "home_score": None, "away_score": None}
        plays = [self.play("g1", 1, "A", "B", 0.2), self.play("g2", 2, "B", "A", 0.1)]
        result = build_season(2024, self.teams, [*self.games, incomplete], plays)
        self.assertEqual(list(result["weeks"]), ["1"])
        incomplete.update(home_score=3, away_score=0)
        result = build_season(2024, self.teams, [*self.games, incomplete], plays)
        self.assertEqual(list(result["weeks"]), ["1"])

    def test_only_completed_regular_season_games(self):
        class Rows:
            def to_dicts(self):
                return [*self_games, {**self_games[0], "home_score": None},
                        {**self_games[0], "game_type": "POST"}]

        self_games = self.games
        self.assertEqual(completed_games(Rows()), self.games)

    def test_strength_of_schedule_uses_current_opponent_ratings_and_game_weights(self):
        games = [
            {"season": 2024, "week": week, "game_type": "REG", "home_team": "A",
             "away_team": opponent, "home_score": 7, "away_score": 7}
            for week, opponent in [(1, "B"), (2, "C"), (3, "B")]
        ]
        games.append({"season": 2024, "week": 4, "game_type": "REG", "home_team": "A",
                      "away_team": "D", "home_score": None, "away_score": None})
        def snapshot(offense, defense):
            return {
                "offense": [{"id": team, "epa": value} for team, value in offense.items()],
                "defense": [{"id": team, "epa": value} for team, value in defense.items()],
                "special": [{"id": team} for team in ("A", "B", "C", "D")],
                "combined": [{"id": team} for team in ("A", "B", "C", "D")],
            }
        data = {"season": 2024, "weeks": {
            "1": snapshot({"A": 0.1, "B": 0.2}, {"A": 0.0, "B": 0.05}),
            "2": snapshot({"A": 0.1, "B": 0.1, "C": 0.4},
                          {"A": 0.0, "B": 0.03, "C": 0.1}),
            "3": snapshot({"A": 0.1, "B": 0.3, "C": 0.9},
                          {"A": 0.0, "B": 0.1, "C": 0.1}),
        }}
        result = add_game_details(data, games)
        def sos(week, metric, team):
            return next(row["strengthOfSchedule"] for row in result["weeks"][week][metric] if row["id"] == team)
        self.assertAlmostEqual(sos("1", "offense", "A"), 0.15)
        self.assertAlmostEqual(sos("2", "offense", "A"), (0.07 + 0.3) / 2)
        for metric in ("offense", "defense", "special", "combined"):
            self.assertAlmostEqual(sos("3", metric, "A"), (0.2 + 0.8 + 0.2) / 3)
            ranks = {row["id"]: row["strengthOfScheduleRank"] for row in result["weeks"]["3"][metric]}
            self.assertEqual(ranks["A"], 1)
            self.assertEqual(ranks["B"], 2)
            self.assertEqual(ranks["C"], 3)
            if "D" in ranks:
                self.assertIsNone(ranks["D"])
        self.assertAlmostEqual(sos("2", "special", "B"), 0.1)
        self.assertIsNone(sos("1", "special", "C"))
        self.assertIsNone(sos("3", "special", "D"))

    def test_strength_of_schedule_is_unavailable_when_any_opponent_lacks_epa(self):
        games = [self.games[0]]
        result = add_game_details({"season": 2024, "weeks": {"1": {
            "offense": [{"id": "A", "epa": 0.2}, {"id": "B", "epa": 0.1}],
            "defense": [{"id": "A", "epa": 0.0}],
        }}}, games)
        self.assertIsNone(result["weeks"]["1"]["offense"][0]["strengthOfSchedule"])
        self.assertIsNone(result["weeks"]["1"]["offense"][0]["strengthOfScheduleRank"])
        self.assertAlmostEqual(result["weeks"]["1"]["offense"][1]["strengthOfSchedule"], 0.2)
        self.assertEqual(result["weeks"]["1"]["offense"][1]["strengthOfScheduleRank"], 1)

    def test_sos_rank_includes_opponents_missing_from_all_metric_rows(self):
        games = [self.games[0], {**self.games[0], "home_team": "C", "away_team": "D"}]
        result = add_game_details({"season": 2024, "weeks": {"1": {
            "offense": [{"id": "A", "epa": 0.2}, {"id": "B", "epa": 0.1}, {"id": "C", "epa": 0.5}],
            "defense": [{"id": "A", "epa": 0.0}, {"id": "B", "epa": 0.0}, {"id": "C", "epa": 0.0}],
            "special": [{"id": "A"}, {"id": "C"}],
        }}}, games)
        ranks = {row["id"]: row["strengthOfScheduleRank"] for row in result["weeks"]["1"]["special"]}
        self.assertEqual(ranks, {"A": 3, "C": None})


if __name__ == "__main__":
    unittest.main()
