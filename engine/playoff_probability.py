"""
Playoff Probability Module

WARNING: This is an unvalidated prototype, not an NFL tiebreaker or complete
mathematical clinching implementation. Do not use its output as official
standings or playoff odds.

Provides two approaches to determining playoff likelihood:
1. Monte Carlo Simulation: Uses EPA data to simulate remaining games
2. Deterministic Analysis: Proves some locks/eliminations from record bounds
"""

import random
from collections import defaultdict
from typing import Callable, Dict, List, Tuple, Optional
from dataclasses import dataclass
from fractions import Fraction
import math

from playoff_standings import Standings


@dataclass
class TeamRecord:
    """Represents a team's record at a snapshot in time."""
    team_id: str
    wins: int
    losses: int
    ties: int
    division: str
    conference: str
    
    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties
    
    @property
    def win_pct(self) -> float:
        if self.games_played == 0:
            return 0.0
        return (self.wins + self.ties / 2) / self.games_played


@dataclass
class GameOutcome:
    """Represents a simulated game outcome."""
    home_team: str
    away_team: str
    home_wins: bool
    tie: bool = False


class MonteCarloSimulator:
    """
    Simulates remaining regular season games using EPA data to estimate win probabilities.
    
    Uses expected points added (EPA) differentials to estimate the probability of each team
    winning their remaining games, then runs Monte Carlo simulations to calculate playoff odds.
    """
    
    def __init__(self, num_simulations: int = 10000):
        """
        Initialize the simulator.
        
        Args:
            num_simulations: Number of Monte Carlo simulations to run
        """
        self.num_simulations = num_simulations

    def epa_to_win_probability(
        home_epa: float,
        away_epa: float,
        intercept: float = 0.37727851012243907,
        epa_coefficient: float = 7.5792877384478725,
    ) -> float:
        """
        Estimate P(home win | no tie).

        Coefficients must be fitted using the same EPA
        definition and historical pregame data.
        """
        delta_epa = home_epa - away_epa
        log_odds = intercept + epa_coefficient * delta_epa

        if log_odds >= 0:
            return 1.0 / (1.0 + math.exp(-log_odds))

        exp_log_odds = math.exp(log_odds)
        return exp_log_odds / (1.0 + exp_log_odds)
    
    def simulate_game(self, home_team: str, away_team: str, 
                     epa_ratings: Dict[str, float], seed: Optional[int] = None) -> GameOutcome:
        """
        Simulate a single game outcome.
        
        Args:
            home_team: Home team ID
            away_team: Away team ID
            epa_ratings: Dict mapping team IDs to their combined EPA ratings
            seed: Optional random seed for reproducibility
            
        Returns:
            GameOutcome with result
        """
        if seed is not None:
            random.seed(seed)
        
        home_epa = epa_ratings.get(home_team, 0.0)
        away_epa = epa_ratings.get(away_team, 0.0)
        
        win_prob = self.epa_to_win_probability(home_epa, away_epa)
        
        # Ties are rare but possible (roughly 1 in 500 games)
        tie_chance = 0.002
        rand = random.random()
        
        if rand < tie_chance:
            return GameOutcome(home_team, away_team, home_wins=False, tie=True)
        elif rand < tie_chance + (1 - tie_chance) * win_prob:
            return GameOutcome(home_team, away_team, home_wins=True)
        else:
            return GameOutcome(home_team, away_team, home_wins=False)
    
    def simulate_season(self, records: Dict[str, TeamRecord],
                       schedule: List[Tuple[str, str]],
                       epa_ratings: Dict[str, float],
                       outcomes: Optional[List[Tuple[str, str, int]]] = None) -> Dict[str, TeamRecord]:
        """
        Simulate remaining games for all teams given a schedule.
        
        Args:
            records: Current team records
            schedule: List of (home_team, away_team) tuples for remaining games
            epa_ratings: EPA ratings for each team
            
        Returns:
            Updated records after simulating remaining games
        """
        final_records = {team_id: TeamRecord(
            team_id=record.team_id,
            wins=record.wins,
            losses=record.losses,
            ties=record.ties,
            division=record.division,
            conference=record.conference,
        ) for team_id, record in records.items()}
        
        for home_team, away_team in schedule:
            outcome = self.simulate_game(home_team, away_team, epa_ratings)
            if outcomes is not None:
                outcomes.append((home_team, away_team, 1 if outcome.tie else 2 if outcome.home_wins else 0))
            
            if outcome.tie:
                final_records[home_team].ties += 1
                final_records[away_team].ties += 1
            elif outcome.home_wins:
                final_records[home_team].wins += 1
                final_records[away_team].losses += 1
            else:
                final_records[home_team].losses += 1
                final_records[away_team].wins += 1
        
        return final_records
    
    def calculate_playoff_odds(self, records: Dict[str, TeamRecord],
                              schedule: List[Tuple[str, str]],
                              epa_ratings: Dict[str, float],
                              playoff_teams_per_conference: int = 7,
                              game_history: Optional[List[Tuple[str, str, int]]] = None,
                              progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, float]:
        """
        Run Monte Carlo simulations to calculate playoff probability for each team.
        
        Args:
            records: Current team records
            schedule: Remaining games
            epa_ratings: EPA ratings for each team
            playoff_teams_per_conference: Number of teams making playoffs per conference (typically 7)
            
        Returns:
            Dict mapping team IDs to playoff probability (0-1)
        """
        playoff_counts = defaultdict(int)
        
        for index in range(self.num_simulations):
            outcomes = list(game_history) if game_history is not None else None
            final_records = self.simulate_season(records, schedule, epa_ratings, outcomes)
            if outcomes is None:
                playoff_teams = self._get_playoff_teams(final_records, playoff_teams_per_conference)
            else:
                standings = Standings(final_records, outcomes)
                playoff_teams = set().union(*(standings.playoff_teams(conference, playoff_teams_per_conference)
                                              for conference in ("AFC", "NFC")))
            for team_id in playoff_teams:
                playoff_counts[team_id] += 1
            completed = index + 1
            if progress is not None and (completed % 1000 == 0 or completed == self.num_simulations):
                progress(completed, self.num_simulations)
        
        odds = {
            team_id: playoff_counts.get(team_id, 0) / self.num_simulations
            for team_id in records.keys()
        }
        
        return odds
    
    @staticmethod
    def _get_playoff_teams(records: Dict[str, TeamRecord], 
                          playoff_teams_per_conference: int) -> set:
        """
        Determine which teams make the playoffs from a final record dict.
        
        Uses NFL playoff seeding: division winners (first place in division),
        then wild card teams (best records among non-division-winners).
        
        Args:
            records: Final team records
            playoff_teams_per_conference: Teams per conference in playoffs
            
        Returns:
            Set of team IDs that make the playoffs
        """
        playoff_teams = set()
        
        for conference in {"AFC", "NFC"}:
            conf_teams = {
                team_id: record for team_id, record in records.items()
                if record.conference == conference
            }
            
            if not conf_teams:
                continue
            
            divisions = defaultdict(list)
            for team_id, record in conf_teams.items():
                divisions[record.division].append((team_id, record))
            
            # Div winners (usually 4 per conference)
            for div_teams in divisions.values():
                div_winner = max(div_teams, key=lambda x: (x[1].win_pct, x[0]))
                playoff_teams.add(div_winner[0])
            
            # Wild cards: remaining spots filled by best records
            non_winners = [
                (team_id, record) for team_id, record in conf_teams.items()
                if team_id not in playoff_teams
            ]
            
            wildcard_count = playoff_teams_per_conference - len(divisions)
            wild_cards = sorted(non_winners, key=lambda x: (-x[1].win_pct, x[0]))[:wildcard_count]
            
            for team_id, _ in wild_cards:
                playoff_teams.add(team_id)
        
        return playoff_teams


class DeterministicPlayoffAnalyzer:
    """Conservative clinching proofs from record bounds, not NFL tiebreakers.

    An undetermined result is not proof that a team is still in contention.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def max_wins(record: TeamRecord, games_remaining: int) -> int:
        """Calculate the maximum possible wins for a team."""
        return record.wins + games_remaining
    
    @staticmethod
    def min_wins(record: TeamRecord) -> int:
        """Calculate the minimum possible wins a team will have."""
        return record.wins

    @staticmethod
    def _bounds(record: TeamRecord, remaining: int):
        if not isinstance(remaining, int) or isinstance(remaining, bool) or remaining < 0:
            raise ValueError(f"Invalid games remaining for {record.team_id}.")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
               for value in (record.wins, record.losses, record.ties)):
            raise ValueError(f"Invalid record for {record.team_id}.")
        total = record.games_played + remaining
        if not total:
            raise ValueError(f"No games available for {record.team_id}.")
        return (Fraction(2 * record.wins + record.ties, 2 * total),
                Fraction(2 * (record.wins + remaining) + record.ties, 2 * total))

    def _conference_bounds(self, team_record, other_records, team_games_remaining, other_games_remaining):
        if team_record.team_id in other_records:
            raise ValueError("The subject team must not appear in other_records.")
        if any(team_id != record.team_id for team_id, record in other_records.items()):
            raise ValueError("Record keys must match team IDs.")
        conference = {team_id: record for team_id, record in other_records.items()
                      if record.conference == team_record.conference}
        conference[team_record.team_id] = team_record
        divisions = defaultdict(list)
        for record in conference.values():
            divisions[record.division].append(record.team_id)
        if (team_record.conference not in ("AFC", "NFC") or len(conference) != 16
                or len(divisions) != 4 or any(not division or len(teams) != 4
                                               for division, teams in divisions.items())):
            raise ValueError("A complete conference with four teams in each of four divisions is required.")
        bounds = {}
        for team_id, record in conference.items():
            if team_id == team_record.team_id:
                remaining = team_games_remaining
            else:
                if team_id not in other_games_remaining:
                    raise ValueError(f"Missing games remaining for {team_id}.")
                remaining = other_games_remaining[team_id]
            bounds[team_id] = self._bounds(record, remaining)
        return conference, bounds
    
    def is_mathematically_eliminated(self, 
                                     team_record: TeamRecord,
                                     other_records: Dict[str, TeamRecord],
                                     team_games_remaining: int,
                                     other_games_remaining: Dict[str, int]) -> bool:
        """Return True only when record bounds prove elimination."""
        conference, bounds = self._conference_bounds(
            team_record, other_records, team_games_remaining, other_games_remaining)
        subject_max = bounds[team_record.team_id][1]
        definitely_ahead = [
            record for team_id, record in conference.items()
            if team_id != team_record.team_id and bounds[team_id][0] > subject_max
        ]
        return (len(definitely_ahead) >= 7
                and any(record.division == team_record.division for record in definitely_ahead))
    
    def is_mathematically_locked(self,
                                team_record: TeamRecord,
                                other_records: Dict[str, TeamRecord],
                                team_games_remaining: int,
                                other_games_remaining: Dict[str, int]) -> bool:
        """Return True only when record bounds prove a division or playoff berth."""
        conference, bounds = self._conference_bounds(
            team_record, other_records, team_games_remaining, other_games_remaining)
        subject_min = bounds[team_record.team_id][0]
        possible_ahead = [
            record for team_id, record in conference.items()
            if team_id != team_record.team_id and bounds[team_id][1] >= subject_min
        ]
        return (not any(record.division == team_record.division for record in possible_ahead)
                or len(possible_ahead) <= 2)
    
    def analyze_playoff_status(self,
                              records: Dict[str, TeamRecord],
                              games_remaining: Dict[str, int]) -> Dict[str, str]:
        """
        Analyze playoff status for all teams.
        
        Args:
            records: Dict of team records
            games_remaining: Dict mapping team IDs to games remaining
            
        Returns:
            Dict mapping team IDs to status:
            - "locked_in": Mathematically made playoffs
            - "eliminated": Mathematically out of playoffs  
            - "undetermined": These bounds cannot prove either outcome
        """
        status = {}
        
        for team_id, record in records.items():
            if team_id not in games_remaining:
                raise ValueError(f"Missing games remaining for {team_id}.")
            remaining = games_remaining[team_id]
            others = {tid: rec for tid, rec in records.items() if tid != team_id}
            others_remaining = {tid: games_remaining[tid] for tid in others if tid in games_remaining}
            
            if self.is_mathematically_locked(record, others, remaining, others_remaining):
                status[team_id] = "locked_in"
            elif self.is_mathematically_eliminated(record, others, remaining, others_remaining):
                status[team_id] = "eliminated"
            else:
                status[team_id] = "undetermined"
        
        return status


def calculate_remaining_schedule(all_games: List[Dict],
                                current_week: int,
                                week_cutoff: int = 18) -> List[Tuple[str, str]]:
    """
    Extract remaining games from full schedule.
    
    Args:
        all_games: List of game dicts with 'week', 'home_team', 'away_team', 'home_score', 'away_score'
        current_week: Current week (games through this week are complete)
        week_cutoff: Last week to include (usually 18)
        
    Returns:
        List of (home_team, away_team) tuples for remaining games
    """
    remaining = []
    for game in all_games:
        week = game.get("week", 0)
        if week > current_week and week <= week_cutoff:
            if game.get("home_score") is None or game.get("away_score") is None:
                remaining.append((game["home_team"], game["away_team"]))
    
    return remaining


def extract_records_at_week(season_data: Dict,
                           week: int) -> Dict[str, TeamRecord]:
    """
    Extract team records at a specific week from season data.
    
    Args:
        season_data: Season data dict from engine with weeks snapshot
        week: Which week to extract records from
        
    Returns:
        Dict mapping team IDs to TeamRecord objects
    """
    if str(week) not in season_data.get("weeks", {}):
        return {}
    
    snapshot = season_data["weeks"][str(week)]["offense"]
    records = {}
    
    for team_data in snapshot:
        team_id = team_data["id"]
        record = team_data.get("record", {})
        team_info = {k: v for k, v in team_data.items()}
        
        records[team_id] = TeamRecord(
            team_id=team_id,
            wins=record.get("wins", 0),
            losses=record.get("losses", 0),
            ties=record.get("ties", 0),
            division=team_data.get("division", ""),
            conference=team_data.get("conference", ""),
        )
    
    return records


def extract_epa_ratings(season_data: Dict, week: int) -> Dict[str, float]:
    """
    Extract combined EPA ratings at a specific week.
    
    Args:
        season_data: Season data dict from engine
        week: Which week to extract EPA from
        
    Returns:
        Dict mapping team IDs to combined EPA rating
    """
    if str(week) not in season_data.get("weeks", {}):
        return {}
    
    snapshot = season_data["weeks"][str(week)].get("combined", [])
    return {team["id"]: team.get("epa", 0.0) for team in snapshot}
