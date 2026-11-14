import type { Team } from './types.js';

export function escapeHtml(value: string | number) {
  const entities: Record<string, string> = {
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  };
  return String(value).replace(/[&<>"']/g, character => entities[character]);
}

document.addEventListener('error', event => {
  if (event.target instanceof HTMLImageElement && event.target.matches('.team-badge img')) {
    event.target.hidden = true;
    event.target.parentElement?.classList.remove('team-badge-with-logo');
  }
}, true);

export function badge(team: Team, large = false) {
  const color = /^#[0-9a-f]{6}$/i.test(team.color) ? team.color : '#274c37';
  let logo = '';
  if (team.logo) {
    try {
      const url = new URL(team.logo);
      if (url.protocol === 'https:') logo = `<img src="${escapeHtml(url.href)}" alt="" loading="lazy">`;
    } catch {
      console.error(`Invalid logo URL for ${team.id}`);
    }
  }
  return `<span class="team-badge${large ? ' team-badge-large' : ''}${logo ? ' team-badge-with-logo' : ''}" style="--team-color: ${color}" aria-hidden="true">${escapeHtml(team.id)}${logo}</span>`;
}

export function movement(team: { change: number | null }) {
  if (team.change === null) return '<span class="movement neutral" aria-label="No previous ranking">—</span>';
  if (team.change === 0) return '<span class="movement neutral" aria-label="No change">—</span>';
  const direction = team.change > 0 ? 'up' : 'down';
  return `<span class="movement ${direction}" aria-label="${direction === 'up' ? 'Up' : 'Down'} ${Math.abs(team.change)} ${Math.abs(team.change) === 1 ? 'place' : 'places'}"><span aria-hidden="true">${direction === 'up' ? '▲' : '▼'}</span> ${Math.abs(team.change)}</span>`;
}
