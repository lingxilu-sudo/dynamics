/**
 * plotter.js — X-T 图绘制器
 * Canvas 2D 绘制 10 秒平滑滚动时序图
 */

class XTPlotter {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.WINDOW_SEC = 10;
    this.Y_MIN = 0.0;
    this.Y_MAX = 4.0;
  }

  render(state, params) {
    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const w = this.canvas.width / dpr;
    const h = this.canvas.height / dpr;
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const hist_t = state.history_t;
    const hist_x = state.history_x;
    if (hist_t.length < 2) {
      this._drawAxes(ctx, w, h, 0, this.WINDOW_SEC);
      ctx.restore();
      return;
    }

    const t_now = hist_t.last();
    let t_start, t_end;
    if (t_now <= this.WINDOW_SEC) {
      t_start = 0;
      t_end = this.WINDOW_SEC;
    } else {
      t_end = t_now;
      t_start = t_end - this.WINDOW_SEC;
    }

    this._drawAxes(ctx, w, h, t_start, t_end);
    this._drawEqLine(ctx, w, h, t_start, t_end, state);
    this._drawCurve(ctx, w, h, t_start, t_end, hist_t, hist_x);
    ctx.restore();
  }

  _tToX(t, w, t_start, t_end) {
    const margin_l = 50, margin_r = 10;
    return margin_l + (t - t_start) / (t_end - t_start) * (w - margin_l - margin_r);
  }
  _yToY(val, h) {
    const margin_t = 10, margin_b = 35;
    return margin_t + (1 - (val - this.Y_MIN) / (this.Y_MAX - this.Y_MIN)) * (h - margin_t - margin_b);
  }

  _drawAxes(ctx, w, h, t_start, t_end) {
    const margin_l = 50, margin_r = 10, margin_t = 10, margin_b = 35;
    const plotW = w - margin_l - margin_r;
    const plotH = h - margin_t - margin_b;

    // Grid
    ctx.strokeStyle = C_GRID;
    ctx.lineWidth = 0.5;
    ctx.globalAlpha = 0.15;
    ctx.setLineDash([4, 4]);

    // Vertical grid (time ticks every 2s)
    const tickInterval = 2;
    const firstTick = Math.ceil(t_start / tickInterval) * tickInterval;
    for (let t = firstTick; t <= t_end; t += tickInterval) {
      const x = this._tToX(t, w, t_start, t_end);
      ctx.beginPath();
      ctx.moveTo(x, margin_t);
      ctx.lineTo(x, h - margin_b);
      ctx.stroke();
    }

    // Horizontal grid
    for (let v = Math.ceil(this.Y_MIN); v <= this.Y_MAX; v += 0.5) {
      const y = this._yToY(v, h);
      ctx.beginPath();
      ctx.moveTo(margin_l, y);
      ctx.lineTo(w - margin_r, y);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;

    // Axes border
    ctx.strokeStyle = C_GRID;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;
    ctx.strokeRect(margin_l, margin_t, plotW, plotH);
    ctx.globalAlpha = 1.0;

    // X-axis labels
    ctx.fillStyle = C_GRID;
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (let t = firstTick; t <= t_end; t += tickInterval) {
      const x = this._tToX(t, w, t_start, t_end);
      ctx.fillText(t.toFixed(0), x, h - margin_b + 4);
    }

    // Y-axis labels
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let v = Math.ceil(this.Y_MIN); v <= this.Y_MAX; v += 1) {
      const y = this._yToY(v, h);
      ctx.fillText(v.toFixed(1), margin_l - 5, y);
    }

    // Axis titles
    ctx.fillStyle = C_LABEL;
    ctx.font = '11px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('t (s)', margin_l + plotW / 2, h - 14);
    ctx.save();
    ctx.translate(14, margin_t + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textBaseline = 'middle';
    ctx.fillText('x (m)', 0, 0);
    ctx.restore();
  }

  _drawEqLine(ctx, w, h, t_start, t_end, state) {
    if (state.is_stuck) return;
    const y = this._yToY(state.x_eq, h);
    const margin_l = 50, margin_r = 10;

    ctx.setLineDash([5, 3]);
    ctx.strokeStyle = '#00FF88';
    ctx.lineWidth = 1.2;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(margin_l, y);
    ctx.lineTo(w - margin_r, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;

    ctx.fillStyle = '#00FF88';
    ctx.font = '10px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText(`x_eq=${state.x_eq.toFixed(2)}`, margin_l + 5, y - 3);
  }

  _drawCurve(ctx, w, h, t_start, t_end, hist_t, hist_x) {
    // Binary search for start index
    const margin = 0.5;
    const t_clip = t_start - margin;
    let lo = 0, hi = hist_t.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (hist_t.get(mid) < t_clip) lo = mid + 1;
      else hi = mid;
    }

    // Draw glow
    ctx.beginPath();
    let first = true;
    for (let i = lo; i < hist_t.length; i++) {
      const t = hist_t.get(i);
      if (t > t_end + 0.1) break;
      const x = this._tToX(t, w, t_start, t_end);
      const y = this._yToY(hist_x.get(i), h);
      if (first) { ctx.moveTo(x, y); first = false; }
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = C_FORCE_FRICTION;
    ctx.lineWidth = 5;
    ctx.globalAlpha = 0.15;
    ctx.stroke();

    // Draw main line
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.9;
    ctx.stroke();
    ctx.globalAlpha = 1.0;
  }
}
