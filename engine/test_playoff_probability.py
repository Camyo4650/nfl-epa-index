import unittest
from itertools import product
from unittest.mock import patch
from playoff_probability import (
    TeamRecord, GameOutcome, MonteCarloSimulator, DeterministicPlayoffAnalyzer,
    calculate_remaining_schedule, extract_records_at_week, extract_epa_ratings
)


class TestTeamRecord(unittest.TestCase):
    def test_games_played_calculation(self):
        record = TeamRecord("KC", wins=10, losses=4, ties=1, division="AFC West", conference="AFC")
        self.assertEqual(record.games_played, 15)
    
    def test_win_pct_calculation(self):
        record = TeamRecord("KC", wins=12, losses=4, ties=0, division="AFC West", conference="AFC")
        self.assertAlmostEqual(record.win_pct, 0.75, places=4)
    
    def test_win_pct_zero_games(self):
        record = TeamRecord("KC", wins=0, losses=0, ties=0, division="AFC West", conference="AFC")
        self.assertEqual(record.win_pct, 0.0)

    def test_win_pct_counts_ties_as_half_a_win(self):
        record = TeamRecord("KC", wins=8, losses=8, ties=1, division="AFC West", conference="AFC")
        self.assertEqual(record.win_pct, 0.5)


class TestMonteCarloSimulator(unittest.TestCase):
    def setUp(self):
        self.simulator = MonteCarloSimulator(num_simulations=100)
        self.records = {
            "KC": TeamRecord("KC", wins=10, losses=4, ties=0, division="AFC West", conference="AFC"),
            "LAC": TeamRecord("LAC", wins=5, losses=9, ties=0, division="AFC West", conference="AFC"),
        }
        self.epa_ratings = {"KC": 2.5, "LAC": -1.2}
    
    def test_epa_to_win_probability_equal_teams(self):
        prob = self.simulator.epa_to_win_probability(0.0, 0.0)
        self.assertAlmostEqual(prob, 0.5932165, places=6)

    def test_epa_probability_uses_per_play_scale(self):
        self.assertAlmostEqual(self.simulator.epa_to_win_probability(0.1, 0.0), 0.7568, delta=0.0001)
        self.assertAlmostEqual(self.simulator.epa_to_win_probability(0.0, 0.1), 0.406, delta=0.0005)
    
    def test_epa_to_win_probability_strong_home(self):
        prob_strong = self.simulator.epa_to_win_probability(5.0, 0.0)
        prob_weak = self.simulator.epa_to_win_probability(0.0, 5.0)
        self.assertGreater(prob_strong, prob_weak)
    
    def test_epa_to_win_probability_bounds(self):
        # Should always be between 0 and 1
        for home_epa in [-5, 0, 5]:
            for away_epa in [-5, 0, 5]:
                prob = self.simulator.epa_to_win_probability(home_epa, away_epa)
                self.assertGreaterEqual(prob, 0.0)
                self.assertLessEqual(prob, 1.0)
    
    def test_simulate_game(self):
        outcome = self.simulator.simulate_game("KC", "LAC", self.epa_ratings)
        self.assertIsInstance(outcome, GameOutcome)
        self.assertEqual(outcome.home_team, "KC")
        self.assertEqual(outcome.away_team, "LAC")
        self.assertIsInstance(outcome.home_wins, bool)
        self.assertIsInstance(outcome.tie, bool)
    
    def test_simulate_game_deterministic_seed(self):
        outcome1 = self.simulator.simulate_game("KC", "LAC", self.epa_ratings, seed=42)
        outcome2 = self.simulator.simulate_game("KC", "LAC", self.epa_ratings, seed=42)
        self.assertEqual(outcome1.home_wins, outcome2.home_wins)
        self.assertEqual(outcome1.tie, outcome2.tie)

    def test_simulate_game_win_probability_is_conditional_on_no_tie(self):
        with patch.object(self.simulator, "epa_to_win_probability", return_value=0.5):
            with patch("playoff_probability.random.random", return_value=0.5005):
                outcome = self.simulator.simulate_game("KC", "LAC", self.epa_ratings)
        self.assertTrue(outcome.home_wins)
        with patch.object(self.simulator, "epa_to_win_probability", return_value=0.5):
            with patch("playoff_probability.random.random", return_value=0.5015):
                outcome = self.simulator.simulate_game("KC", "LAC", self.epa_ratings)
        self.assertFalse(outcome.home_wins)
        self.assertFalse(outcome.tie)
    
    def test_simulate_season(self):
        schedule = [("KC", "LAC"), ("LAC", "KC")]
        final_records = self.simulator.simulate_season(self.records, schedule, self.epa_ratings)
        
        for team_id in self.records:
            self.assertIn(team_id, final_records)
            # Games should have increased
            self.assertGreaterEqual(
                final_records[team_id].games_played,
                self.records[team_id].games_played + 1
            )
    
    def test_calculate_playoff_odds_basic(self):
        schedule = [("KC", "LAC"), ("KC", "LAC"), ("KC", "LAC"), ("KC", "LAC")]
        odds = self.simulator.calculate_playoff_odds(self.records, schedule, self.epa_ratings)
        
        self.assertIn("KC", odds)
        self.assertIn("LAC", odds)
        self.assertGreaterEqual(odds["KC"], 0.0)
        self.assertLessEqual(odds["KC"], 1.0)
        # KC should have higher or equal odds than LAC given better record and EPA
        self.assertGreaterEqual(odds["KC"], odds["LAC"])

    def test_progress_reports_each_thousand_and_final_remainder(self):
        self.simulator.num_simulations = 2501
        updates = []
        self.simulator.calculate_playoff_odds(
            self.records, [], self.epa_ratings,
            progress=lambda completed, total: updates.append((completed, total)))
        self.assertEqual(updates, [(1000, 2501), (2000, 2501), (2501, 2501)])
    
    def test_get_playoff_teams_basic(self):
        # Create a scenario with clear winners
        records = {
            "KC": TeamRecord("KC", wins=14, losses=2, ties=0, division="AFC West", conference="AFC"),
            "LAC": TeamRecord("LAC", wins=5, losses=11, ties=0, division="AFC West", conference="AFC"),
            "BAL": TeamRecord("BAL", wins=13, losses=3, ties=0, division="AFC North", conference="AFC"),
            "PIT": TeamRecord("PIT", wins=10, losses=6, ties=0, division="AFC North", conference="AFC"),
            "BUF": TeamRecord("BUF", wins=12, losses=4, ties=0, division="AFC East", conference="AFC"),
            "MIA": TeamRecord("MIA", wins=9, losses=7, ties=0, division="AFC East", conference="AFC"),
            "NE": TeamRecord("NE", wins=4, losses=12, ties=0, division="AFC East", conference="AFC"),
            "IND": TeamRecord("IND", wins=11, losses=5, ties=0, division="AFC South", conference="AFC"),
            "HOU": TeamRecord("HOU", wins=6, losses=10, ties=0, division="AFC South", conference="AFC"),
        }
        
        playoff_teams = self.simulator._get_playoff_teams(records, 7)
        self.assertEqual(len(playoff_teams), 7)
        # Division winners should be in playoff_teams
        self.assertIn("KC", playoff_teams)  # AFC West winner
        self.assertIn("BAL", playoff_teams)  # AFC North winner
        self.assertIn("BUF", playoff_teams)  # AFC East winner
        self.assertIn("IND", playoff_teams)  # AFC South winner


class TestDeterministicPlayoffAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = DeterministicPlayoffAnalyzer()
        self.records = {
            f"T{i}": TeamRecord(f"T{i}", 7, 6, 0, f"Division {i // 4}", "AFC")
            for i in range(16)
        }
        self.remaining = {team_id: 4 for team_id in self.records}

    def analyze(self):
        return self.analyzer.analyze_playoff_status(self.records, self.remaining)

    def test_max_wins_calculation(self):
        record = TeamRecord("KC", wins=10, losses=4, ties=0, division="AFC West", conference="AFC")
        max_wins = self.analyzer.max_wins(record, 2)
        self.assertEqual(max_wins, 12)
    
    def test_min_wins_calculation(self):
        record = TeamRecord("KC", wins=10, losses=4, ties=0, division="AFC West", conference="AFC")
        min_wins = self.analyzer.min_wins(record)
        self.assertEqual(min_wins, 10)
    
    def test_better_records_are_not_elimination_proof(self):
        self.records["T0"].wins, self.records["T0"].losses = 6, 7
        self.assertEqual(self.analyze()["T0"], "undetermined")

    def test_division_winner_is_locked_despite_other_strong_teams(self):
        self.records["T0"].wins, self.records["T0"].losses = 13, 0
        self.assertEqual(self.analyze()["T0"], "locked_in")

    def test_elimination_requires_both_division_and_wildcard_exclusion(self):
        self.records["T0"].wins, self.records["T0"].losses = 0, 13
        self.assertEqual(self.analyze()["T0"], "eliminated")
        for i in range(1, 4):
            self.records[f"T{i}"].wins, self.records[f"T{i}"].losses = 0, 13
        self.assertEqual(self.analyze()["T0"], "undetermined")

    def test_equal_record_bounds_do_not_prove_a_division_clinch(self):
        self.records["T0"].wins, self.records["T0"].losses = 11, 2
        self.assertEqual(self.analyze()["T0"], "undetermined")

    def test_ties_count_half_and_unequal_games_use_percentages(self):
        self.records["T0"] = TeamRecord("T0", 8, 4, 1, "Division 0", "AFC")
        for i in range(1, 4):
            self.records[f"T{i}"] = TeamRecord(f"T{i}", 5, 6, 2, "Division 0", "AFC")
        self.remaining.update({f"T{i}": 1 for i in range(4)})
        self.assertEqual(self.analyze()["T0"], "locked_in")

    def test_missing_data_is_an_error(self):
        del self.remaining["T5"]
        with self.assertRaisesRegex(ValueError, "Missing games remaining"):
            self.analyze()
        del self.records["T5"]
        with self.assertRaisesRegex(ValueError, "complete conference"):
            self.analyze()

    def test_proven_statuses_survive_every_outcome_of_a_remaining_week(self):
        wins = [13, 5, 5, 2, 12, 10, 9, 8, 11, 10, 8, 7, 9, 8, 6, 3]
        for i, count in enumerate(wins):
            self.records[f"T{i}"].wins = count
            self.records[f"T{i}"].losses = 16 - count
        self.remaining = {team_id: 1 for team_id in self.records}
        status = self.analyze()
        self.assertIn("locked_in", status.values())
        self.assertIn("eliminated", status.values())
        for outcomes in product(("home", "away", "tie"), repeat=8):
            final = {team_id: TeamRecord(
                team_id, record.wins, record.losses, record.ties, record.division, record.conference
            ) for team_id, record in self.records.items()}
            for i, outcome in enumerate(outcomes):
                home, away = final[f"T{2 * i}"], final[f"T{2 * i + 1}"]
                if outcome == "tie":
                    home.ties += 1
                    away.ties += 1
                elif outcome == "home":
                    home.wins += 1
                    away.losses += 1
                else:
                    away.wins += 1
                    home.losses += 1
            selected = MonteCarloSimulator._get_playoff_teams(final, 7)
            for team_id, value in status.items():
                if value == "locked_in":
                    self.assertIn(team_id, selected)
                elif value == "eliminated":
                    self.assertNotIn(team_id, selected)


class TestHelperFunctions(unittest.TestCase):
    def test_calculate_remaining_schedule(self):
        games = [
            {"week": 1, "home_team": "KC", "away_team": "LAC", "home_score": 20, "away_score": 10},
            {"week": 2, "home_team": "LAC", "away_team": "KC", "home_score": None, "away_score": None},
            {"week": 2, "home_team": "BUF", "away_team": "MIA", "home_score": None, "away_score": None},
            {"week": 3, "home_team": "KC", "away_team": "BUF", "home_score": None, "away_score": None},
        ]
        
        remaining = calculate_remaining_schedule(games, current_week=1, week_cutoff=18)
        self.assertEqual(len(remaining), 3)
        self.assertIn(("LAC", "KC"), remaining)
        self.assertIn(("BUF", "MIA"), remaining)
        self.assertIn(("KC", "BUF"), remaining)
    
    def test_calculate_remaining_schedule_respects_cutoff(self):
        games = [
            {"week": 1, "home_team": "KC", "away_team": "LAC", "home_score": 20, "away_score": 10},
            {"week": 18, "home_team": "LAC", "away_team": "KC", "home_score": None, "away_score": None},
            {"week": 19, "home_team": "BUF", "away_team": "MIA", "home_score": None, "away_score": None},
        ]
        
        remaining = calculate_remaining_schedule(games, current_week=1, week_cutoff=18)
        self.assertEqual(len(remaining), 1)
        self.assertIn(("LAC", "KC"), remaining)
    
    def test_extract_records_at_week(self):
        season_data = {
            "weeks": {
                "1": {
                    "offense": [
                        {
                            "id": "KC",
                            "record": {"wins": 1, "losses": 0, "ties": 0},
                            "conference": "AFC",
                            "division": "AFC West",
                        },
                        {
                            "id": "LAC",
                            "record": {"wins": 0, "losses": 1, "ties": 0},
                            "conference": "AFC",
                            "division": "AFC West",
                        },
                    ]
                }
            }
        }
        
        records = extract_records_at_week(season_data, 1)
        self.assertEqual(len(records), 2)
        self.assertEqual(records["KC"].wins, 1)
        self.assertEqual(records["LAC"].losses, 1)
    
    def test_extract_epa_ratings(self):
        season_data = {
            "weeks": {
                "1": {
                    "combined": [
                        {"id": "KC", "epa": 2.5},
                        {"id": "LAC", "epa": -1.2},
                    ]
                }
            }
        }
        
        ratings = extract_epa_ratings(season_data, 1)
        self.assertEqual(ratings["KC"], 2.5)
        self.assertEqual(ratings["LAC"], -1.2)


if __name__ == "__main__":
    unittest.main()
