import unittest
from unittest.mock import patch

from playoffs import build_playoff_picture


class PlayoffPictureTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for i in range(32):
            self.rows.append({
                "id": f"T{i:02}", "name": f"Team {i}",
                "conference": "AFC" if i < 16 else "NFC",
                "division": f"Division {(i % 16) // 4}",
                "color": "#123456", "logo": None,
                "record": {"wins": 8, "losses": 8, "ties": 0}, "epa": 0.1,
            })
        self.data = {"season": 2025, "weeks": {"16": {"offense": self.rows, "combined": self.rows}}}
        self.games = [
            {"season": 2025, "game_type": "REG", "week": week,
             "home_team": f"T{i:02}", "away_team": f"T{i+1:02}",
             "home_score": 21, "away_score": 14}
            for week in range(1, 18) for i in range(0, 32, 2)
        ]

    def test_future_scores_do_not_leak_into_simulation(self):
        with patch("playoffs.MonteCarloSimulator.calculate_playoff_odds") as simulate:
            simulate.return_value = {row["id"]: 0.5 for row in self.rows}
            picture = build_playoff_picture(self.data, self.games, 16)
        schedule = simulate.call_args.args[1]
        self.assertEqual(len(schedule), 16)
        self.assertEqual(schedule[0], ("T00", "T01"))
        history = simulate.call_args.kwargs["game_history"]
        self.assertEqual(len(history), 16 * 16)
        self.assertTrue(all(result == 2 for _, _, result in history))
        for conference in ("AFC", "NFC"):
            teams = picture["conferences"][conference]
            self.assertEqual(len(teams), 16)
            self.assertEqual([team["rank"] for team in teams], list(range(1, 17)))
            self.assertEqual(sum(team["divisionLeader"] for team in teams[:4]), 4)
            self.assertEqual(teams[0]["probability"], 0.5)
            self.assertEqual(teams[0]["status"], "undetermined")

    def test_simulations_produce_seven_expected_berths_per_conference(self):
        progress = []
        picture = build_playoff_picture(self.data, self.games, 16, simulations=20,
                                        progress=lambda completed, total: progress.append((completed, total)))
        self.assertEqual(progress, [(20, 20)])
        for conference in ("AFC", "NFC"):
            self.assertAlmostEqual(sum(team["probability"] for team in picture["conferences"][conference]), 7)

    def test_incomplete_schedule_and_missing_epa_fail(self):
        with self.assertRaisesRegex(ValueError, "complete regular-season schedule"):
            build_playoff_picture(self.data, self.games[:-1], 16)
        self.data["weeks"]["16"]["combined"] = self.rows[:-1]
        with self.assertRaisesRegex(ValueError, "32 team"):
            build_playoff_picture(self.data, self.games, 16)

    def test_missing_week_fails(self):
        with self.assertRaisesRegex(ValueError, "No completed ranking snapshot"):
            build_playoff_picture(self.data, self.games, 15)

    def test_missing_completed_score_fails(self):
        self.games[0]["home_score"] = None
        with self.assertRaisesRegex(ValueError, "Missing completed game score"):
            build_playoff_picture(self.data, self.games, 16)

    def postseason_games(self):
        games = []
        for start in (0, 16):
            for home, away in ((4, 1), (8, 5), (12, 9)):
                games.append({"season": 2025, "game_type": "WC",
                              "home_team": f"T{start + home:02}", "away_team": f"T{start + away:02}"})
            for home, away in ((0, 1), (4, 5)):
                games.append({"season": 2025, "game_type": "DIV",
                              "home_team": f"T{start + home:02}", "away_team": f"T{start + away:02}"})
        return games

    def test_completed_season_uses_postseason_qualifiers_not_provisional_tiebreaks(self):
        for row in self.rows:
            row["record"] = {"wins": 9, "losses": 8, "ties": 0}
        self.data["weeks"]["18"] = self.data["weeks"]["16"]
        with patch("playoffs.MonteCarloSimulator.calculate_playoff_odds") as simulate:
            picture = build_playoff_picture(self.data, self.games + self.postseason_games(), 18)
        simulate.assert_not_called()
        self.assertEqual(picture["statusSource"], "postseason")
        self.assertEqual(picture["simulations"], 0)
        for conference, start in (("AFC", 0), ("NFC", 16)):
            teams = picture["conferences"][conference]
            expected = {f"T{start + i:02}" for i in (0, 1, 4, 5, 8, 9, 12)}
            self.assertEqual({team["id"] for team in teams[:7]}, expected)
            for team in teams:
                self.assertEqual(team["status"], "locked_in" if team["id"] in expected else "eliminated")
                self.assertEqual(team["probability"], float(team["id"] in expected))
            self.assertEqual({team["id"] for team in teams if team["divisionLeader"]},
                             {f"T{start + i:02}" for i in (0, 4, 8, 12)})

    def test_postseason_information_not_used_for_previous_week(self):
        picture = build_playoff_picture(self.data, self.games + self.postseason_games(), 16, simulations=20)
        self.assertEqual(picture["statusSource"], "record_bounds")
        self.assertEqual(picture["simulations"], 20)
        self.assertTrue(any(team["status"] == "undetermined"
                            for teams in picture["conferences"].values() for team in teams))

    def test_incomplete_postseason_does_not_claim_final_results(self):
        for row in self.rows:
            row["record"] = {"wins": 9, "losses": 8, "ties": 0}
        self.data["weeks"]["18"] = self.data["weeks"]["16"]
        picture = build_playoff_picture(self.data, self.games + self.postseason_games()[:6], 18, simulations=2)
        self.assertEqual(picture["statusSource"], "record_bounds")
        self.assertTrue(any(team["status"] == "undetermined"
                            for teams in picture["conferences"].values() for team in teams))

    def test_invalid_complete_postseason_fails_explicitly(self):
        for row in self.rows:
            row["record"] = {"wins": 9, "losses": 8, "ties": 0}
        self.data["weeks"]["18"] = self.data["weeks"]["16"]
        postseason = self.postseason_games()
        postseason[0]["away_team"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "Invalid postseason bracket"):
            build_playoff_picture(self.data, self.games + postseason, 18)

    def test_2020_final_week_is_week_17(self):
        self.data["season"] = 2020
        self.data["weeks"]["17"] = self.data["weeks"]["16"]
        games = [{**game, "season": 2020} for game in self.games if game["week"] <= 16]
        games.extend({**game, "season": 2020} for game in self.postseason_games())
        picture = build_playoff_picture(self.data, games, 17)
        self.assertEqual(picture["statusSource"], "postseason")
        for teams in picture["conferences"].values():
            self.assertEqual(sum(team["status"] == "locked_in" for team in teams), 7)
            self.assertEqual(sum(team["status"] == "eliminated" for team in teams), 9)

    def test_canceled_2022_buffalo_cincinnati_game(self):
        self.data["season"] = 2022
        self.rows[0]["id"], self.rows[1]["id"] = "BUF", "CIN"
        for row in self.rows[2:]:
            row["record"] = {"wins": 9, "losses": 8, "ties": 0}
        self.data["weeks"]["18"] = self.data["weeks"]["16"]
        games = []
        for game in self.games:
            if game["week"] == 17 and game["home_team"] == "T00":
                continue
            home = {"T00": "BUF", "T01": "CIN"}.get(game["home_team"], game["home_team"])
            away = {"T00": "BUF", "T01": "CIN"}.get(game["away_team"], game["away_team"])
            games.append({**game, "season": 2022, "home_team": home, "away_team": away})
        picture = build_playoff_picture(self.data, games, 18, simulations=2)
        self.assertEqual(picture["statusSource"], "record_bounds")
