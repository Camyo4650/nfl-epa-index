import { badge, escapeHtml } from './components.js';
import { formatRecord } from './rankings.js';
import type { RecordData, Team } from './types.js';

export interface PlayoffTeam extends Team {
  record: RecordData;
  rank: number;
  divisionLeader: boolean;
  probability: number;
  status: 'locked_in' | 'eliminated' | 'undetermined';
}

export function renderPlayoffTeams(teams: PlayoffTeam[], finalResults = false) {
  return teams.map(team => {
    const labels = [
      team.divisionLeader ? 'DIVISION LEADER' : team.rank <= 7 ? 'WILD CARD' : '',
      team.status === 'locked_in' ? 'CLINCHED' : team.status === 'eliminated' ? 'ELIMINATED' : ''
    ].filter(Boolean);
    return `<article class="playoff-card${team.rank <= 7 ? ' playoff-card-in' : ''}${team.status === 'eliminated' ? ' playoff-card-eliminated' : ''}">
      <span class="playoff-rank">${String(team.rank).padStart(2, '0')}</span>
      ${badge(team)}
      <div class="playoff-team"><h3>${escapeHtml(team.name)}</h3><span>${escapeHtml(team.conference)} ${escapeHtml(team.division)} · ${formatRecord(team.record)}</span>${labels.length ? `<small>${labels.join(' · ')}</small>` : ''}</div>
      <div class="playoff-probability"><strong>${(team.probability * 100).toFixed(1)}%</strong><span>${finalResults ? 'FINAL RESULT' : 'EST. CHANCE'}</span></div>
    </article>`;
  }).join('');
}
