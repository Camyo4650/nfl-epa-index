"""Provisional standings using game results for the leading NFL tiebreakers."""

from collections import defaultdict
from fractions import Fraction


def _percentage(results):
    return Fraction(sum(results), 2 * len(results)) if results else None


class Standings:
    def __init__(self, records, games):
        self.records = records
        self.results = defaultdict(list)
        for home, away, home_result in games:
            if home not in records or away not in records or home_result not in (0, 1, 2):
                raise ValueError("Invalid game outcome in playoff standings.")
            self.results[home].append((away, home_result))
            self.results[away].append((home, 2 - home_result))

    def _record(self, team, opponents):
        return _percentage([result for opponent, result in self.results[team] if opponent in opponents])

    def _conference_record(self, team):
        record = self.records[team]
        opponents = {other for other in self.records if self.records[other].conference == record.conference}
        return self._record(team, opponents)

    def _division_record(self, team):
        record = self.records[team]
        opponents = {other for other in self.records
                     if self.records[other].conference == record.conference
                     and self.records[other].division == record.division}
        return self._record(team, opponents)

    def _common_records(self, teams, minimum):
        common = set.intersection(*(set(opponent for opponent, _ in self.results[team]) for team in teams))
        values = {}
        for team in teams:
            results = [result for opponent, result in self.results[team] if opponent in common]
            if len(results) < minimum:
                return None
            values[team] = _percentage(results)
        return values

    def _head_to_head(self, teams, division):
        values = {team: self._record(team, set(teams) - {team}) for team in teams}
        if any(value is None for value in values.values()):
            return None
        if division or len(teams) == 2:
            return values
        # A multi-team wild-card head-to-head tiebreaker requires a sweep.
        wins_all = {team for team in teams if all(
            any(opponent == other and result == 2 for opponent, result in self.results[team])
            and not any(opponent == other and result != 2 for opponent, result in self.results[team])
            for other in teams if other != team)}
        loses_all = {team for team in teams if all(
            any(opponent == other and result == 0 for opponent, result in self.results[team])
            and not any(opponent == other and result != 0 for opponent, result in self.results[team])
            for other in teams if other != team)}
        if wins_all:
            return {team: int(team in wins_all) for team in teams}
        if loses_all:
            return {team: int(team not in loses_all) for team in teams}
        return None

    def _strength(self, team, victories_only):
        opponents = [opponent for opponent, result in self.results[team]
                     if not victories_only or result == 2]
        results = [result for opponent in opponents for _, result in self.results[opponent]]
        return _percentage(results)

    def _break_tie(self, candidates, division):
        teams = list(candidates)
        while len(teams) > 1:
            steps = [
                lambda group: self._head_to_head(group, division),
                *([lambda group: {team: self._division_record(team) for team in group}] if division else []),
                *([] if division else [lambda group: {team: self._conference_record(team) for team in group}]),
                lambda group: self._common_records(group, 1 if division else 4),
                *([lambda group: {team: self._conference_record(team) for team in group}] if division else []),
                lambda group: {team: self._strength(team, True) for team in group},
                lambda group: {team: self._strength(team, False) for team in group},
            ]
            reduced = False
            for step in steps:
                values = step(teams)
                if values is None or any(value is None for value in values.values()):
                    continue
                best = max(values.values())
                winners = [team for team in teams if values[team] == best]
                if len(winners) < len(teams):
                    teams = winners
                    reduced = True
                    break
            if not reduced:
                return min(teams)
        return teams[0]

    def _winner(self, teams, division=False):
        best = max(self.records[team].win_pct for team in teams)
        tied = [team for team in teams if self.records[team].win_pct == best]
        if len(tied) == 1:
            return tied[0]
        if not division:
            by_division = defaultdict(list)
            for team in tied:
                by_division[self.records[team].division].append(team)
            tied = [self._break_tie(group, True) if len(group) > 1 else group[0]
                    for group in by_division.values()]
        return self._break_tie(tied, division) if len(tied) > 1 else tied[0]

    def order(self, teams, division=False):
        remaining = list(teams)
        ordered = []
        while remaining:
            winner = self._winner(remaining, division)
            ordered.append(winner)
            remaining.remove(winner)
        return ordered

    def conference_picture(self, conference):
        teams = [team for team, record in self.records.items() if record.conference == conference]
        if not teams:
            return [], set()
        divisions = defaultdict(list)
        for team in teams:
            divisions[self.records[team].division].append(team)
        leaders = {self._winner(group, True) for group in divisions.values()}
        champions = self.order(leaders)
        rest = self.order(team for team in teams if team not in leaders)
        return champions + rest, leaders

    def playoff_teams(self, conference, slots):
        teams = [team for team, record in self.records.items() if record.conference == conference]
        if not teams:
            return set()
        divisions = defaultdict(list)
        for team in teams:
            divisions[self.records[team].division].append(team)
        leaders = {self._winner(group, True) for group in divisions.values()}
        remaining = set(teams) - leaders
        selected = set(leaders)
        for _ in range(min(max(0, slots - len(leaders)), len(remaining))):
            winner = self._winner(remaining)
            selected.add(winner)
            remaining.remove(winner)
        return selected
