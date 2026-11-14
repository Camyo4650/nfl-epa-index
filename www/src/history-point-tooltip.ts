export function setupPointTooltip(chart: HTMLElement, tooltip: HTMLElement) {
  function hide() {
    tooltip.hidden = true;
  }

  chart.addEventListener('pointermove', event => {
    const point = event.target instanceof Element ? event.target.closest<SVGElement>('.history-point-hit') : null;
    if (!point || event.pointerType === 'touch') {
      hide();
      return;
    }
    tooltip.textContent = `${point.dataset.name} · Week ${point.dataset.week} · Rank ${point.dataset.rank}`;
    tooltip.hidden = false;
    const margin = 8;
    const left = Math.min(event.clientX + 14, window.innerWidth - tooltip.offsetWidth - margin);
    const top = event.clientY + 16 + tooltip.offsetHeight <= window.innerHeight - margin
      ? event.clientY + 16 : event.clientY - tooltip.offsetHeight - 12;
    tooltip.style.left = `${Math.max(margin, left)}px`;
    tooltip.style.top = `${Math.max(margin, top)}px`;
  });
  chart.addEventListener('pointerleave', hide);
  window.addEventListener('scroll', hide, true);
  window.addEventListener('resize', hide);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') hide();
  });
  return hide;
}
