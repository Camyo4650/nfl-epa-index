"""Fit the playoff game model on 2016–2018 and evaluate it on 2019.

Run from the repository root with ``engine/.venv/bin/python -m engine.calibrate_playoff_model``.
The evaluation season is not used to fit the coefficients.
"""

import math
from collections import defaultdict

import nflreadpy as nfl


def observations(season):
    games = [game for game in nfl.load_schedules(season).to_dicts()
             if game["game_type"] == "REG" and game["home_score"] is not None
             and game["away_score"] is not None]
    game_ids = {game["game_id"] for game in games}
    plays = nfl.load_pbp(season).select(
        "game_id", "season_type", "week", "play_type", "epa", "posteam", "defteam",
        "qb_kneel", "qb_spike", "play_deleted",
    ).to_dicts()
    totals = defaultdict(float)
    counts = defaultdict(int)
    samples = []
    for week in sorted({game["week"] for game in games}):
        for game in games:
            if game["week"] != week or game["home_score"] == game["away_score"]:
                continue
            home, away = game["home_team"], game["away_team"]
            if counts[home] and counts[away]:
                samples.append((totals[home] / counts[home] - totals[away] / counts[away],
                                int(game["home_score"] > game["away_score"])))
        for play in plays:
            epa = play["epa"]
            if (play["week"] != week or play["game_id"] not in game_ids
                    or play["season_type"] != "REG"
                    or play["play_type"] not in ("pass", "run", "kickoff", "punt", "field_goal", "extra_point")
                    or epa is None or not math.isfinite(epa)
                    or not play["posteam"] or not play["defteam"]
                    or play["qb_kneel"] or play["qb_spike"] or play["play_deleted"]):
                continue
            offense, defense = play["posteam"], play["defteam"]
            totals[offense] += epa
            totals[defense] -= epa
            counts[offense] += 1
            counts[defense] += 1
    return samples


def fit(samples):
    intercept = coefficient = 0.0
    for _ in range(30):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for difference, outcome in samples:
            probability = 1 / (1 + math.exp(-intercept - coefficient * difference))
            weight = probability * (1 - probability)
            g0 += outcome - probability
            g1 += (outcome - probability) * difference
            h00 += weight
            h01 += weight * difference
            h11 += weight * difference * difference
        determinant = h00 * h11 - h01 * h01
        if determinant <= 0:
            raise ValueError("Insufficient variation to fit the EPA model.")
        delta_intercept = (g0 * h11 - g1 * h01) / determinant
        delta_coefficient = (g1 * h00 - g0 * h01) / determinant
        intercept += delta_intercept
        coefficient += delta_coefficient
        if abs(delta_intercept) + abs(delta_coefficient) < 1e-10:
            return intercept, coefficient
    raise ValueError("EPA model fitting did not converge.")


def metrics(samples, intercept, coefficient):
    probabilities = [1 / (1 + math.exp(-intercept - coefficient * difference))
                     for difference, _ in samples]
    brier = sum((probability - outcome) ** 2
                for probability, (_, outcome) in zip(probabilities, samples)) / len(samples)
    log_loss = sum(-outcome * math.log(probability) - (1 - outcome) * math.log1p(-probability)
                   for probability, (_, outcome) in zip(probabilities, samples)) / len(samples)
    return brier, log_loss


def main():
    training = [sample for season in range(2016, 2019) for sample in observations(season)]
    held_out = observations(2019)
    intercept, coefficient = fit(training)
    print(f"Training games: {len(training)}; held-out games: {len(held_out)}")
    print(f"Intercept: {intercept:.15f}; EPA coefficient: {coefficient:.15f}")
    for label, samples in (("Training", training), ("Held-out 2019", held_out)):
        for model, slope in (("EPA", coefficient), ("constant home", 0.0)):
            brier, loss = metrics(samples, intercept, slope)
            print(f"{label} {model}: Brier {brier:.6f}, log loss {loss:.6f}")


if __name__ == "__main__":
    main()
