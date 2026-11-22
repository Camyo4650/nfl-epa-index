import unittest
from unittest.mock import patch

import calibrate_playoff_model as calibration


class Table:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *columns):
        return self

    def to_dicts(self):
        return self.rows


class CalibrationTests(unittest.TestCase):
    def test_features_use_only_completed_previous_weeks(self):
        games = [
            {"game_id": "one", "game_type": "REG", "week": 1,
             "home_team": "A", "away_team": "B", "home_score": 7, "away_score": 3},
            {"game_id": "two", "game_type": "REG", "week": 2,
             "home_team": "A", "away_team": "B", "home_score": 3, "away_score": 7},
        ]
        plays = [
            {"game_id": game_id, "season_type": "REG", "week": week,
             "play_type": "pass", "epa": epa, "posteam": "A", "defteam": "B",
             "qb_kneel": False, "qb_spike": False, "play_deleted": False}
            for game_id, week, epa in (("one", 1, 0.1), ("two", 2, 1.0))
        ]
        with patch.object(calibration.nfl, "load_schedules", return_value=Table(games)), \
                patch.object(calibration.nfl, "load_pbp", return_value=Table(plays)):
            self.assertEqual(calibration.observations(2019), [(0.2, 0)])

    def test_metric_for_equal_predictions(self):
        brier, loss = calibration.metrics([(0.0, 0), (0.0, 1)], 0.0, 0.0)
        self.assertAlmostEqual(brier, 0.25)
        self.assertAlmostEqual(loss, 0.69314718056)


if __name__ == "__main__":
    unittest.main()
