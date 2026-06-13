/**
 * renderer.js — 场景渲染器
 * Canvas 2D 绘制物理场景（墙壁、传送带、弹簧、方块、力箭头）
 */

// ---- 配色 ----
const C_BG = '#1A1A2E';
const C_BG_PLOT = '#0F0F23';
const C_WALL_FILL = '#16213E';
const C_WALL_EDGE = '#0F3460';
const C_BELT = '#4A4A6A';
const C_BELT_STRIPE = '#5A5A8A';
const C_BLOCK = '#7D26CD';
const C_BLOCK_EDGE = '#FFFFFF';
const C_FORCE_SPRING = '#FF3366';
const C_FORCE_FRICTION = '#00D2FF';
const C_FORCE_NET = '#00FF88';
const C_GRID = '#8888AA';
const C_LABEL = '#CCCCDD';
const C_GRAVITY = '#FF8800';
const C_NORMAL = '#FFD700';

// ---- 场景几何 ----
const SCENE_X_MIN = -0.5;
const SCENE_X_MAX = 9.0;
const SCENE_Y_MIN = -0.5;
const SCENE_Y_MAX = 3.5;
const WALL_X = 0.0;
const WALL_H = 3.2;
const BELT_Y0 = 0.3;
const BELT_H = 0.4;
const BLOCK_H = 1.0;
const ROLLER_R = 0.28;
const N_SPRING_COILS = 12;
const FORCE_SCALE = 0.8;

class SceneRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this._beltShift = 0;
    this._prevT = 0;
  }

  _toPixel(sx, sy) {
    const w = this._w || this.canvas.width;
    const h = this._h || this.canvas.height;
    const px = (sx - SCENE_X_MIN) / (SCENE_X_MAX - SCENE_X_MIN) * w;
    const py = (1 - (sy - SCENE_Y_MIN) / (SCENE_Y_MAX - SCENE_Y_MIN)) * h;
    return [px, py];
  }

  _scaleX(dx) {
    const w = this._w || this.canvas.width;
    return dx / (SCENE_X_MAX - SCENE_X_MIN) * w;
  }
  _scaleY(dy) {
    const h = this._h || this.canvas.height;
    return dy / (SCENE_Y_MAX - SCENE_Y_MIN) * h;
  }

  render(state, params) {
    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const w = this.canvas.width / dpr;
    const h = this.canvas.height / dpr;
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    this._w = w;
    this._h = h;
    this._drawWall(ctx);
    this._drawBelt(ctx, state, params);
    this._drawSpring(ctx, state);
    this._drawBlock(ctx, state);
    this._drawForceArrows(ctx, state);
    this._drawMarkers(ctx, state, params);
    this._drawLegend(ctx);
    this._drawCollision(ctx, state);
    ctx.restore();
  }

  _drawRoundRect(ctx, x, y, w, h, r, fill, stroke) {
    const [px, py] = this._toPixel(x, y + h);
    const pw = this._scaleX(w);
    const ph = this._scaleY(h);
    const pr = Math.min(this._scaleX(r), pw/2, ph/2);
    ctx.beginPath();
    ctx.moveTo(px + pr, py);
    ctx.lineTo(px + pw - pr, py);
    ctx.quadraticCurveTo(px + pw, py, px + pw, py + pr);
    ctx.lineTo(px + pw, py + ph - pr);
    ctx.quadraticCurveTo(px + pw, py + ph, px + pw - pr, py + ph);
    ctx.lineTo(px + pr, py + ph);
    ctx.quadraticCurveTo(px, py + ph, px, py + ph - pr);
    ctx.lineTo(px, py + pr);
    ctx.quadraticCurveTo(px, py, px + pr, py);
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
  }

  _drawWall(ctx) {
    this._drawRoundRect(ctx, WALL_X, 0, WALL_W, WALL_H, 0.02, C_WALL_FILL, C_WALL_EDGE);
  }

  _drawBelt(ctx, state, params) {
    const belt_x0 = WALL_X + WALL_W + 0.1;
    const belt_w = SCENE_X_MAX - belt_x0 + 0.1;

    // Belt body
    this._drawRoundRect(ctx, belt_x0, BELT_Y0, belt_w, BELT_H, 0.02, C_BELT, '#5A5A8A');

    // Rollers
    const rl_cx = belt_x0;
    const rl_cy = BELT_Y0 + BELT_H / 2;
    const rr_cx = belt_x0 + belt_w;
    const rr_cy = rl_cy;
    this._drawCircle(ctx, rl_cx, rl_cy, ROLLER_R, '#3A3A5A', C_BELT_STRIPE);
    this._drawCircle(ctx, rr_cx, rr_cy, ROLLER_R, '#3A3A5A', C_BELT_STRIPE);
    this._drawCircle(ctx, rl_cx, rl_cy, 0.04, C_BELT_STRIPE, null);
    this._drawCircle(ctx, rr_cx, rr_cy, 0.04, C_BELT_STRIPE, null);

    // Belt stripes (incremental shift)
    const dt = state.t - this._prevT;
    this._prevT = state.t;
    const n_stripes = 12;
    const spacing = belt_w / n_stripes;
    this._beltShift += params.v_belt * dt;
    this._beltShift = ((this._beltShift % spacing) + spacing) % spacing;

    ctx.strokeStyle = C_BELT_STRIPE;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.7;
    for (let i = 0; i < n_stripes + 2; i++) {
      let sx = belt_x0 + spacing * i + this._beltShift;
      if (sx > belt_x0 + belt_w) sx -= (n_stripes + 2) * spacing;
      if (sx >= belt_x0 && sx <= belt_x0 + belt_w) {
        const [px, py1] = this._toPixel(sx, BELT_Y0);
        const [, py2] = this._toPixel(sx, BELT_Y0 + BELT_H);
        ctx.beginPath();
        ctx.moveTo(px, py1);
        ctx.lineTo(px, py2);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1.0;
  }

  _drawCircle(ctx, cx, cy, r, fill, stroke) {
    const [px, py] = this._toPixel(cx, cy);
    const pr = this._scaleX(r);
    ctx.beginPath();
    ctx.arc(px, py, pr, 0, Math.PI * 2);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
  }

  _drawSpring(ctx, state) {
    const spring_x0 = WALL_X + WALL_W;
    const block_left = WALL_X + WALL_W + state.x - BLOCK_W / 2;
    const spring_y = BELT_Y0 + BELT_H + BLOCK_H * 0.5;
    const spring_len = Math.max(block_left - spring_x0, 0.05);
    const coil_n = Math.max(4, Math.round(N_SPRING_COILS * spring_len / L0));
    const n_pts = Math.max(9, coil_n * 4 + 1);
    const amplitude = Math.min(0.22, Math.max(0.06, 0.18 * spring_len / L0));

    // Generate zigzag
    ctx.beginPath();
    for (let i = 0; i < n_pts; i++) {
      const t = i / (n_pts - 1);
      const sx = spring_x0 + spring_len * t;
      const phase = (coil_n * t) % 1.0;
      let saw;
      if (phase < 0.25) saw = 4 * phase;
      else if (phase < 0.5) saw = 2 - 4 * phase;
      else if (phase < 0.75) saw = 4 * phase - 2;
      else saw = 4 - 4 * phase;
      let sy = spring_y + amplitude * saw;
      if (i === 0 || i === n_pts - 1) sy = spring_y;

      const [px, py] = this._toPixel(sx, sy);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    // Glow
    ctx.strokeStyle = '#AAAAAA';
    ctx.lineWidth = 5;
    ctx.globalAlpha = 0.15;
    ctx.stroke();
    // Main line
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.9;
    ctx.stroke();
    ctx.globalAlpha = 1.0;
  }

  _drawBlock(ctx, state) {
    const block_cx = WALL_X + WALL_W + state.x;
    const block_x = block_cx - BLOCK_W / 2;
    const block_y = BELT_Y0 + BELT_H;

    this._drawRoundRect(ctx, block_x, block_y, BLOCK_W, BLOCK_H, 0.05, C_BLOCK, C_BLOCK_EDGE);

    // Velocity label
    const [px, py] = this._toPixel(block_cx, block_y + BLOCK_H / 2);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = `bold ${Math.max(10, this._scaleX(0.06))}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`v=${state.v.toFixed(2)}`, px, py);

    // Stuck/Slip indicator
    const [ix, iy] = this._toPixel(block_cx, block_y + BLOCK_H + 0.15);
    ctx.fillStyle = C_FORCE_NET;
    ctx.font = `italic ${Math.max(9, this._scaleX(0.05))}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(state.is_stuck ? 'STUCK' : 'SLIP', ix, iy);
  }

  _drawForceArrows(ctx, state) {
    const block_cx = WALL_X + WALL_W + state.x;
    const block_cy = BELT_Y0 + BELT_H + BLOCK_H / 2;

    const max_f = Math.max(Math.abs(state.F_spring), Math.abs(state.F_friction), Math.abs(state.F_net), 0.01);
    const scale = Math.min(2.5, Math.max(0.3, 1.2 / (max_f / 10 + 1)));

    // Spring force (leftward)
    this._drawArrow(ctx, block_cx, block_cy, block_cx - Math.abs(state.F_spring) * scale, block_cy, C_FORCE_SPRING);
    // Friction force
    this._drawArrow(ctx, block_cx, block_cy, block_cx + state.F_friction * scale, block_cy, C_FORCE_FRICTION);
    // Net force
    this._drawArrow(ctx, block_cx, block_cy, block_cx + state.F_net * scale, block_cy, C_FORCE_NET);

    // Gravity (down)
    const vScale = 0.08;
    this._drawArrow(ctx, block_cx, block_cy, block_cx, block_cy - state.N * vScale, C_GRAVITY);
    // Normal (up)
    this._drawArrow(ctx, block_cx, block_cy, block_cx, block_cy + state.N * vScale, C_NORMAL);
  }

  _drawArrow(ctx, x1, y1, x2, y2, color) {
    const [px1, py1] = this._toPixel(x1, y1);
    const [px2, py2] = this._toPixel(x2, y2);
    const dx = px2 - px1;
    const dy = py2 - py1;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 2) return;

    const headLen = Math.min(12, len * 0.3);
    const angle = Math.atan2(dy, dx);

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.5;

    // Shaft
    ctx.beginPath();
    ctx.moveTo(px1, py1);
    ctx.lineTo(px2 - headLen * Math.cos(angle), py2 - headLen * Math.sin(angle));
    ctx.stroke();

    // Head
    ctx.beginPath();
    ctx.moveTo(px2, py2);
    ctx.lineTo(px2 - headLen * Math.cos(angle - 0.4), py2 - headLen * Math.sin(angle - 0.4));
    ctx.lineTo(px2 - headLen * Math.cos(angle + 0.4), py2 - headLen * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fill();
  }

  _drawMarkers(ctx, state, params) {
    // Natural length line
    const l0_x = WALL_X + WALL_W + L0;
    const [l0px, l0py1] = this._toPixel(l0_x, BELT_Y0 - 0.2);
    const [, l0py2] = this._toPixel(l0_x, BELT_Y0 + BELT_H + BLOCK_H + 0.4);
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = '#999999';
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.moveTo(l0px, l0py1);
    ctx.lineTo(l0px, l0py2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1.0;

    // L0 label
    ctx.fillStyle = '#999999';
    ctx.font = '10px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText(`L0=${L0.toFixed(1)}`, l0px + 3, l0py2);

    // Equilibrium position (only when sliding)
    if (!state.is_stuck) {
      const eq_x = WALL_X + WALL_W + state.x_eq;
      const [eqpx, eqpy1] = this._toPixel(eq_x, BELT_Y0 - 0.2);
      const [, eqpy2] = this._toPixel(eq_x, BELT_Y0 + BELT_H + BLOCK_H + 0.4);
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = '#00FF88';
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.6;
      ctx.beginPath();
      ctx.moveTo(eqpx, eqpy1);
      ctx.lineTo(eqpx, eqpy2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1.0;

      ctx.fillStyle = '#00FF88';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`x_eq=${state.x_eq.toFixed(2)}`, eqpx + 3, eqpy2);
    }
  }

  _drawLegend(ctx) {
    const items = [
      [C_FORCE_SPRING, 'F_spring (Spring)'],
      [C_FORCE_FRICTION, 'F_friction (Friction)'],
      [C_FORCE_NET, 'F_net (Net Force)'],
      [C_GRAVITY, 'mg (Gravity)'],
      [C_NORMAL, 'N (Normal)'],
    ];
    const startX = this._scaleX(6.0);
    let y = 30;
    ctx.font = '11px monospace';
    ctx.textBaseline = 'middle';
    for (const [color, label] of items) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(startX, y);
      ctx.lineTo(startX + 25, y);
      ctx.stroke();
      ctx.fillStyle = C_LABEL;
      ctx.textAlign = 'left';
      ctx.fillText(label, startX + 32, y);
      y += 22;
    }
  }

  _drawCollision(ctx, state) {
    if (state.has_collision && state.collision_timer > 0) {
      const alpha = Math.min(1.0, state.collision_timer);
      const [px, py] = this._toPixel((SCENE_X_MAX) / 2, SCENE_Y_MAX - 0.4);
      ctx.fillStyle = `rgba(255, 68, 68, ${alpha})`;
      ctx.font = 'bold 16px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText('Perfectly Inelastic Collision!', px, py);
      state.collision_timer -= 1.0 / 60;
      if (state.collision_timer <= 0) state.has_collision = false;
    }
  }
}
