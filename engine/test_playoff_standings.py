import unittest
from unittest.mock import patch

from playoff_probability import GameOutcome, MonteCarloSimulator, TeamRecord
from playoff_standings import Standings


class PlayoffStandingsTests(unittest.TestCase):
    def setUp(self):
        self.records = {
            "BAL": TeamRecord("BAL", 8, 8, 0, "North", "AFC"),
            "PIT": TeamRecord("PIT", 9, 7, 0, "North", "AFC"),
            "CLE": TeamRecord("CLE", 5, 11, 0, "North", "AFC"),
            "CIN": TeamRecord("CIN", 5, 11, 0, "North", "AFC"),
        }
        # Division results through 2025 Week 17, home result 0/1/2 = loss/tie/win.
        self.history = [
            ("BAL", "CLE", 2), ("CLE", "BAL", 0), ("BAL", "CIN", 0),
            ("CIN", "BAL", 0), ("BAL", "PIT", 0),
            ("PIT", "CLE", 2), ("CLE", "PIT", 2), ("CIN", "PIT", 2),
            ("PIT", "CIN", 2),
        ]

    def test_baltimore_week_18_win_wins_division_on_division_record(self):
        simulator = MonteCarloSimulator(num_simulations=1)
        with patch.object(simulator, "simulate_game", return_value=GameOutcome("PIT", "BAL", False)):
            odds = simulator.calculate_playoff_odds(
                self.records, [("PIT", "BAL")], {team: 0.0 for team in self.records},
                playoff_teams_per_conference=1, game_history=self.history)
        self.assertEqual(odds["BAL"], 1.0)
        self.assertEqual(odds["PIT"], 0.0)

    def test_pittsburgh_win_wins_division(self):
        simulator = MonteCarloSimulator(num_simulations=1)
        with patch.object(simulator, "simulate_game", return_value=GameOutcome("PIT", "BAL", True)):
            odds = simulator.calculate_playoff_odds(
                self.records, [("PIT", "BAL")], {team: 0.0 for team in self.records},
                playoff_teams_per_conference=1, game_history=self.history)
        self.assertEqual(odds["BAL"], 0.0)
        self.assertEqual(odds["PIT"], 1.0)

    def test_head_to_head_precedes_division_record(self):
        records = {
            "A": TeamRecord("A", 9, 8, 0, "North", "AFC"),
            "B": TeamRecord("B", 9, 8, 0, "North", "AFC"),
            "C": TeamRecord("C", 4, 13, 0, "North", "AFC"),
        }
        games = [("A", "B", 2), ("B", "C", 2), ("B", "C", 2), ("A", "C", 0)]
        order, leaders = Standings(records, games).conference_picture("AFC")
        self.assertIn("A", leaders)
        self.assertEqual(order[0], "A")

    def test_wild_card_tie_uses_conference_record(self):
        records = {
            "A": TeamRecord("A", 9, 8, 0, "North", "AFC"),
            "B": TeamRecord("B", 9, 8, 0, "South", "AFC"),
            "C": TeamRecord("C", 4, 13, 0, "West", "AFC"),
            "D": TeamRecord("D", 4, 13, 0, "East", "AFC"),
        }
        standings = Standings(records, [("A", "C", 0), ("B", "D", 2)])
        self.assertEqual(standings.order(["A", "B"]), ["B", "A"])

    def test_division_record_counts_tied_games_as_half(self):
        standings = Standings(self.records, [("BAL", "CLE", 1), ("PIT", "CLE", 0)])
        self.assertEqual(str(standings._division_record("BAL")), "1/2")
        self.assertEqual(str(standings._division_record("PIT")), "0")


if __name__ == "__main__":
    unittest.main()
