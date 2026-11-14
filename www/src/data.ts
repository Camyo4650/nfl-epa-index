// Illustrative data only. Replace these snapshots with a real data source when ready.
export const teams = [
  { id: 'KC', name: 'Kansas City Chiefs', conference: 'AFC', division: 'West', color: '#c8102e' },
  { id: 'BUF', name: 'Buffalo Bills', conference: 'AFC', division: 'East', color: '#00338d' },
  { id: 'BAL', name: 'Baltimore Ravens', conference: 'AFC', division: 'North', color: '#241773' },
  { id: 'CIN', name: 'Cincinnati Bengals', conference: 'AFC', division: 'North', color: '#e65b1c' },
  { id: 'CLE', name: 'Cleveland Browns', conference: 'AFC', division: 'North', color: '#69412e' },
  { id: 'PIT', name: 'Pittsburgh Steelers', conference: 'AFC', division: 'North', color: '#292b30' },
  { id: 'HOU', name: 'Houston Texans', conference: 'AFC', division: 'South', color: '#03202f' },
  { id: 'IND', name: 'Indianapolis Colts', conference: 'AFC', division: 'South', color: '#164b8e' },
  { id: 'JAX', name: 'Jacksonville Jaguars', conference: 'AFC', division: 'South', color: '#006778' },
  { id: 'TEN', name: 'Tennessee Titans', conference: 'AFC', division: 'South', color: '#4b92c8' },
  { id: 'DEN', name: 'Denver Broncos', conference: 'AFC', division: 'West', color: '#d95820' },
  { id: 'LV', name: 'Las Vegas Raiders', conference: 'AFC', division: 'West', color: '#33383c' },
  { id: 'LAC', name: 'Los Angeles Chargers', conference: 'AFC', division: 'West', color: '#0080b5' },
  { id: 'MIA', name: 'Miami Dolphins', conference: 'AFC', division: 'East', color: '#008e97' },
  { id: 'NE', name: 'New England Patriots', conference: 'AFC', division: 'East', color: '#173457' },
  { id: 'NYJ', name: 'New York Jets', conference: 'AFC', division: 'East', color: '#125740' },
  { id: 'PHI', name: 'Philadelphia Eagles', conference: 'NFC', division: 'East', color: '#075a53' },
  { id: 'DAL', name: 'Dallas Cowboys', conference: 'NFC', division: 'East', color: '#365575' },
  { id: 'NYG', name: 'New York Giants', conference: 'NFC', division: 'East', color: '#174893' },
  { id: 'WAS', name: 'Washington Commanders', conference: 'NFC', division: 'East', color: '#773141' },
  { id: 'DET', name: 'Detroit Lions', conference: 'NFC', division: 'North', color: '#0076b6' },
  { id: 'GB', name: 'Green Bay Packers', conference: 'NFC', division: 'North', color: '#1e5542' },
  { id: 'MIN', name: 'Minnesota Vikings', conference: 'NFC', division: 'North', color: '#4f2683' },
  { id: 'CHI', name: 'Chicago Bears', conference: 'NFC', division: 'North', color: '#c35627' },
  { id: 'ATL', name: 'Atlanta Falcons', conference: 'NFC', division: 'South', color: '#a71930' },
  { id: 'CAR', name: 'Carolina Panthers', conference: 'NFC', division: 'South', color: '#0085ca' },
  { id: 'NO', name: 'New Orleans Saints', conference: 'NFC', division: 'South', color: '#84714b' },
  { id: 'TB', name: 'Tampa Bay Buccaneers', conference: 'NFC', division: 'South', color: '#b02a30' },
  { id: 'ARI', name: 'Arizona Cardinals', conference: 'NFC', division: 'West', color: '#97233f' },
  { id: 'LAR', name: 'Los Angeles Rams', conference: 'NFC', division: 'West', color: '#2252a0' },
  { id: 'SF', name: 'San Francisco 49ers', conference: 'NFC', division: 'West', color: '#aa2636' },
  { id: 'SEA', name: 'Seattle Seahawks', conference: 'NFC', division: 'West', color: '#224b65' }
];

// Each array is ordered from rank 1 to rank 32.
export const weeklyRankings = {
  8: ['KC', 'DET', 'BUF', 'BAL', 'PHI', 'SF', 'HOU', 'GB', 'MIN', 'PIT', 'WAS', 'ATL', 'CIN', 'LAC', 'DEN', 'TB', 'SEA', 'ARI', 'DAL', 'IND', 'CHI', 'MIA', 'LAR', 'NYJ', 'NO', 'JAX', 'NE', 'CLE', 'LV', 'TEN', 'NYG', 'CAR'],
  9: ['DET', 'KC', 'BAL', 'BUF', 'PHI', 'GB', 'SF', 'PIT', 'HOU', 'MIN', 'WAS', 'CIN', 'LAC', 'ATL', 'DEN', 'ARI', 'TB', 'SEA', 'LAR', 'DAL', 'IND', 'CHI', 'MIA', 'NYJ', 'NO', 'JAX', 'NE', 'CLE', 'TEN', 'LV', 'NYG', 'CAR'],
  10: ['DET', 'BUF', 'KC', 'BAL', 'PHI', 'PIT', 'GB', 'SF', 'MIN', 'HOU', 'LAC', 'WAS', 'CIN', 'ARI', 'DEN', 'ATL', 'LAR', 'TB', 'SEA', 'IND', 'DAL', 'MIA', 'CHI', 'JAX', 'NYJ', 'NO', 'NE', 'TEN', 'CLE', 'LV', 'NYG', 'CAR']
};

// Fictional week 8 wins and week 9/10 results (1 = win, 0.5 = tie, 0 = loss).
const sampleResults = {
  KC: [7, 1, 0], BUF: [6, 1, 1], BAL: [6, 1, 0], CIN: [4, 1, 1],
  CLE: [2, 0, 0], PIT: [6, 1, 1], HOU: [6, 0, 1], IND: [4, 0, 1],
  JAX: [2, 0.5, 1], TEN: [2, 0.5, 0], DEN: [5, 0, 1], LV: [2, 0, 0],
  LAC: [5, 1, 1], MIA: [3, 0, 1], NE: [2, 0, 1], NYJ: [3, 0, 0],
  PHI: [6, 1, 1], DAL: [4, 0, 0], NYG: [2, 0, 0], WAS: [6, 1, 0],
  DET: [7, 1, 1], GB: [6, 1, 0], MIN: [5, 0, 1], CHI: [4, 0, 0],
  ATL: [5, 0, 0], CAR: [1, 0, 0], NO: [3, 0, 0], TB: [4, 0, 1],
  ARI: [4, 1, 1], LAR: [3, 1, 1], SF: [5, 1, 0], SEA: [4, 0, 1]
};

export const weeklyRecords = Object.fromEntries([8, 9, 10].map(week => [
  week,
  Object.fromEntries(Object.entries(sampleResults).map(([id, results]) => {
    const games = results.slice(1, week - 7);
    const wins = results[0] + games.filter(result => result === 1).length;
    const ties = games.filter(result => result === 0.5).length;
    return [id, { wins, losses: week - wins - ties, ties }];
  }))
]));
