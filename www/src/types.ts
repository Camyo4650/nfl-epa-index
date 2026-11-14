export type Metric = 'offense' | 'defense' | 'special' | 'combined';
export interface Team {
  id: string;
  name: string;
  conference: string;
  division: string;
  color: string;
  secondaryColor?: string;
  logo?: string | null;
}
export interface RecordData { wins: number; losses: number; ties: number }
export type Game = { status: 'played'; opponent: string; home: boolean; teamScore: number; opponentScore: number }
  | { status: 'bye' } | { status: 'unavailable' };
export interface Ranking extends Team {
  rank: number;
  previousRank: number | null;
  change: number | null;
  record: RecordData;
  epa: number;
  strengthOfScheduleRank: number | null;
  points: { for: number; allowed: number; net: number };
  games: { current: Game; previous: Game };
}
export type WeeklySnapshots = Record<string, Record<Metric, Ranking[]>>;
export interface SeasonData { season: number; weeks: WeeklySnapshots }
export interface Selection { rankings: Ranking[]; weeks: WeeklySnapshots; week: number; season: number; metric: Metric }
export interface Status {
  lastSuccessfulRefresh: string | null;
  refreshError: string | null;
  latestSeason: number | null;
  latestWeek: number | null;
}
export interface HistoryTeam { team: Ranking; ranks: Map<number, number> }
