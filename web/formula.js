/**
 * formula.js — 公式面板
 * KaTeX 渲染 LaTeX 数学公式，根据物理阶段切换显示
 */

class FormulaPanel {
  constructor(contentEl, statusEl) {
    this.contentEl = contentEl;
    this.statusEl = statusEl;
    this._currentPhase = null;
    this._prevMuK = null;
  }

  update(state, params) {
    // Force refresh on parameter change
    if (this._prevMuK !== null && Math.abs(params.mu_k - this._prevMuK) > 0.001) {
      this._currentPhase = null;
    }
    this._prevMuK = params.mu_k;

    // Determine phase
    const SHM_THRESHOLD = 30;
    let phase;

    if (state.has_collision && state.collision_timer > 0) {
      phase = 'collision';
    } else if (state.is_stuck) {
      phase = 'stuck';
    } else if (!state.is_stuck && state.friction_stable_steps >= SHM_THRESHOLD) {
      phase = 'shm';
    } else {
      phase = 'sliding';
    }

    if (phase === this._currentPhase) return;
    this._currentPhase = phase;

    if (phase === 'shm') this._showSHM(params);
    else if (phase === 'stuck') this._showStuck();
    else if (phase === 'sliding') this._showSliding();
    else if (phase === 'collision') this._showCollision();
  }

  _render(lines, status) {
    let html = '';
    for (const line of lines) {
      if (line === '') {
        html += '<div style="height:8px;"></div>';
      } else if (line.startsWith('$')) {
        // LaTeX math
        const latex = line.slice(1, -1); // strip $ delimiters
        try {
          html += '<div>' + katex.renderToString(latex, { displayMode: false, throwOnError: false }) + '</div>';
        } catch(e) {
          html += `<div style="color:#FF3366;">${line}</div>`;
        }
      } else {
        // Plain text
        html += `<div style="color:${C_LABEL};">${line}</div>`;
      }
    }
    this.contentEl.innerHTML = html;
    this.statusEl.textContent = status;
  }

  _showSHM(params) {
    const frictionless = params.mu_k < 0.001;
    if (frictionless) {
      this._render([
        '$\\textbf{Simple\\ Harmonic\\ Motion}$',
        '',
        'Frictionless (\\u03BC_k = 0):',
        '$m\\ddot{x} = -k(x - L_0)$',
        '',
        'Restoring force proportional to displacement from L_0',
        '$x_{eq} = L_0$',
        '$\\omega = \\sqrt{k/m},\\quad T = 2\\pi/\\omega$',
        '',
        '$x(t) = (x_0 - L_0)\\cos\\omega t + \\frac{v_0}{\\omega}\\sin\\omega t + L_0$',
        '',
        '$E = \\frac{1}{2}kA^2$ (energy conserved)',
      ], 'Phase: SHM (\u03BC_k = 0)');
    } else {
      this._render([
        '$\\textbf{Simple\\ Harmonic\\ Motion}$',
        '',
        'Friction constant (direction + magnitude):',
        '$f = -\\mu_k mg \\cdot \\mathrm{sgn}(v_{rel}) = \\mathrm{const}$',
        '',
        '$m\\ddot{x} = -k(x - x_{eq})$',
        '$x_{eq} = L_0 - \\frac{\\mu_k mg}{k}\\cdot\\mathrm{sgn}(v_{rel})$',
        '$\\omega = \\sqrt{k/m}$',
        '',
        '$x(t) = (x_0 - x_{eq})\\cos\\omega\\Delta t + \\frac{v_0}{\\omega}\\sin\\omega\\Delta t + x_{eq}$',
        '',
        'Restoring force proportional to displacement from x_eq',
      ], 'Phase: SHM (const friction)');
    }
  }

  _showStuck() {
    this._render([
      '$\\textbf{Stuck\\ Phase\\ (Static\\ Friction)}$',
      '',
      'Block moves with belt:',
      '$v(t) = v_{belt}$',
      '$x(t) = v_{belt} \\cdot (t - t_0) + x_0$',
      '',
      'Condition for sticking:',
      '$|F_{spring}| \\leq \\mu_s \\cdot m \\cdot g$',
      '$k \\cdot |x - L_0| \\leq \\mu_s \\cdot m \\cdot g$',
    ], 'Phase: STUCK (v = v_belt)');
  }

  _showSliding() {
    this._render([
      '$\\textbf{Sliding\\ Phase\\ (Kinetic\\ Friction)}$',
      '',
      '$m\\ddot{x} = -k(x - L_0) - \\mu_k mg\\cdot\\mathrm{sgn}(v_{rel})$',
      '',
      'When sgn(v - v_belt) = const in phase:',
      '$\\Rightarrow m\\ddot{x} = -k(x - x_{eq})$ (SHM)',
      '$x_{eq} = L_0 - \\frac{\\mu_k mg}{k}\\cdot\\mathrm{sgn}(v_{rel})$',
      '$\\omega = \\sqrt{k/m}$',
      '',
      '$x(t) = (x_0 - x_{eq})\\cos\\omega\\Delta t + \\frac{v_0}{\\omega}\\sin\\omega\\Delta t + x_{eq}$',
      '',
      'Valid only while sgn(v - v_belt) unchanged.',
    ], 'Phase: SLIDING');
  }

  _showCollision() {
    this._render([
      '$\\textbf{Wall\\ Collision}$',
      '',
      'Perfectly inelastic:',
      '$v(t^+) = 0$',
      '$x = \\frac{w_{block}}{2}$ (left edge at wall)',
      '',
      'Restarts from rest at wall.',
    ], 'Phase: WALL COLLISION');
  }

  reset() {
    this._currentPhase = null;
    this.contentEl.innerHTML = '';
    this.statusEl.textContent = '';
  }
}
