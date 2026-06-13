/**
 * main.js — 主循环 + 控件绑定
 * requestAnimationFrame 驱动动画，绑定 DOM 控件
 */

const SUBSTEPS = 12;

// ---- 全局对象 ----
let sceneRenderer, xtPlotter, formulaPanel;
let isPlaying = true;
let speedMultiplier = 1;

function resizeCanvases() {
  const sceneCanvas = document.getElementById('scene-canvas');
  const plotCanvas = document.getElementById('plot-canvas');

  const sceneContainer = document.getElementById('scene-container');
  const plotContainer = document.getElementById('plot-container');

  const dpr = window.devicePixelRatio || 1;

  // Scene canvas
  const sw = sceneContainer.clientWidth;
  const sh = sceneContainer.clientHeight;
  sceneCanvas.width = sw * dpr;
  sceneCanvas.height = sh * dpr;
  sceneCanvas.style.width = sw + 'px';
  sceneCanvas.style.height = sh + 'px';

  // Plot canvas
  const pw = plotContainer.clientWidth;
  const ph = plotContainer.clientHeight;
  plotCanvas.width = pw * dpr;
  plotCanvas.height = ph * dpr;
  plotCanvas.style.width = pw + 'px';
  plotCanvas.style.height = ph + 'px';
}

function initControls() {
  // Sliders
  const sliders = [
    { id: 'sl-k', param: 'k', valId: 'val-k' },
    { id: 'sl-mu_k', param: 'mu_k', valId: 'val-mu_k' },
    { id: 'sl-ratio', param: 'ratio', valId: 'val-ratio' },
    { id: 'sl-v_belt', param: 'v_belt', valId: 'val-v_belt' },
    { id: 'sl-m', param: 'm', valId: 'val-m' },
  ];

  for (const s of sliders) {
    const el = document.getElementById(s.id);
    const valEl = document.getElementById(s.valId);
    el.addEventListener('input', () => {
      const val = parseFloat(el.value);
      physicsParams[s.param] = val;
      valEl.textContent = val.toFixed(2);
    });
  }

  // Buttons
  document.getElementById('btn-play').addEventListener('click', () => { isPlaying = true; });
  document.getElementById('btn-pause').addEventListener('click', () => { isPlaying = false; });
  document.getElementById('btn-reset').addEventListener('click', () => {
    physicsReset(physicsState);
    if (formulaPanel) formulaPanel.reset();
    isPlaying = true;
    // Reset sliders to defaults
    document.getElementById('sl-k').value = 3.0;
    document.getElementById('val-k').textContent = '3.00';
    document.getElementById('sl-mu_k').value = 0.25;
    document.getElementById('val-mu_k').textContent = '0.25';
    document.getElementById('sl-ratio').value = 1.6;
    document.getElementById('val-ratio').textContent = '1.60';
    document.getElementById('sl-v_belt').value = 1.5;
    document.getElementById('val-v_belt').textContent = '1.50';
    document.getElementById('sl-m').value = 1.0;
    document.getElementById('val-m').textContent = '1.00';
    physicsParams.k = 3.0;
    physicsParams.mu_k = 0.25;
    physicsParams.ratio = 1.6;
    physicsParams.v_belt = 1.5;
    physicsParams.m = 1.0;
  });

  // Speed buttons
  const speedBtns = document.querySelectorAll('.speed-btn');
  speedBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      speedMultiplier = parseInt(btn.dataset.speed);
      speedBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

function animate() {
  // Physics step
  if (isPlaying) {
    const steps = SUBSTEPS * speedMultiplier;
    for (let i = 0; i < steps; i++) {
      physicsStep(physicsState, physicsParams, DT_PHYS);
    }
  }

  // Render scene
  sceneRenderer.render(physicsState, physicsParams);

  // Render X-T plot
  xtPlotter.render(physicsState, physicsParams);

  // Update formula panel
  formulaPanel.update(physicsState, physicsParams);

  requestAnimationFrame(animate);
}

function init() {
  resizeCanvases();

  const sceneCanvas = document.getElementById('scene-canvas');
  const plotCanvas = document.getElementById('plot-canvas');

  sceneRenderer = new SceneRenderer(sceneCanvas);
  xtPlotter = new XTPlotter(plotCanvas);
  formulaPanel = new FormulaPanel(
    document.getElementById('formula-content'),
    document.getElementById('formula-status')
  );

  initControls();

  // Handle resize
  window.addEventListener('resize', () => {
    resizeCanvases();
  });

  // Start animation
  requestAnimationFrame(animate);
}

// Wait for DOM and KaTeX to load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
