import { requiredElement } from './dom.js';

export function setupMovementExpansion(chartRows: HTMLElement, expandAll: HTMLButtonElement, collapseAll: HTMLButtonElement) {
  function setExpanded(row: Element, expanded: boolean) {
    requiredElement<HTMLButtonElement>('.chart-team-button', row).setAttribute('aria-expanded', String(expanded));
    requiredElement<HTMLElement>('.chart-game-details', row).hidden = !expanded;
  }

  function updateControls() {
    const buttons = [...chartRows.querySelectorAll('.chart-team-button')];
    expandAll.disabled = !buttons.some(button => button.getAttribute('aria-expanded') === 'false');
    collapseAll.disabled = !buttons.some(button => button.getAttribute('aria-expanded') === 'true');
  }

  function setAllExpanded(expanded: boolean) {
    chartRows.querySelectorAll('.chart-row').forEach(row => setExpanded(row, expanded));
    updateControls();
  }

  expandAll.addEventListener('click', () => setAllExpanded(true));
  collapseAll.addEventListener('click', () => setAllExpanded(false));
  chartRows.addEventListener('click', event => {
    const row = event.target instanceof Element ? event.target.closest('.chart-row') : null;
    if (!row || !chartRows.contains(row)) return;
    const button = requiredElement<HTMLButtonElement>('.chart-team-button', row);
    setExpanded(row, button.getAttribute('aria-expanded') !== 'true');
    updateControls();
  });

  return updateControls;
}
