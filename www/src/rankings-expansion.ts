import { requiredElement } from './dom.js';

export function setupRankingsExpansion(body: HTMLElement) {
  const expandedTeams = new Set<string>();
  body.addEventListener('click', event => {
    const row = event.target instanceof Element ? event.target.closest<HTMLElement>('.rankings-row') : null;
    if (!row || !body.contains(row)) return;
    const team = row.dataset.team;
    if (!team) throw new Error('Ranking row is missing its team ID.');
    const button = requiredElement<HTMLButtonElement>('.rankings-team-button', row);
    const expanded = button.getAttribute('aria-expanded') !== 'true';
    if (expanded) expandedTeams.add(team);
    else expandedTeams.delete(team);
    button.setAttribute('aria-expanded', String(expanded));
    requiredElement<HTMLElement>('.rankings-game-details', row).hidden = !expanded;
  });
  return {
    isExpanded: (team: string) => expandedTeams.has(team),
    reset: () => expandedTeams.clear()
  };
}
