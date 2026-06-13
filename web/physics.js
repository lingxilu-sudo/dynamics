/**
 * physics.js — 物理引擎
 * 传送带上的弹簧-质量块系统，支持静摩擦/动摩擦 stick-slip 切换
 */

// ---- 物理常量 ----
const G = 9.81;
const L0 = 1.5;
const WALL_W = 0.3;
const BLOCK_W = 0.12;
const EPS_V = 1e-6;
const DT_PHYS = 0.0008;

// ---- 可调参数 ----
const physicsParams = {
  k: 3.0,
  mu_k: 0.25,
  ratio: 1.6,
  v_belt: 1.5,
  m: 1.0,
  get mu_s() { return this.ratio * this.mu_k; }
};

// ---- 循环缓冲区（高性能历史记录）----
class CircularBuffer {
  constructor(maxLen) {
    this.maxLen = maxLen;
    this.data = new Float64Array(maxLen);
    this.head = 0;
    this.length = 0;
  }
  push(val) {
    this.data[this.head] = val;
    this.head = (this.head + 1) % this.maxLen;
    if (this.length < this.maxLen) this.length++;
  }
  get(i) {
    // i=0 is oldest, i=length-1 is newest
    const start = (this.head - this.length + this.maxLen) % this.maxLen;
    return this.data[(start + i) % this.maxLen];
  }
  last() {
    if (this.length === 0) return 0;
    return this.data[(this.head - 1 + this.maxLen) % this.maxLen];
  }
  clear() {
    this.head = 0;
    this.length = 0;
  }
}

// ---- 物理状态 ----
const physicsState = {
  x: BLOCK_W / 2,
  v: 0.0,
  t: 0.0,
  F_spring: 0.0,
  F_friction: 0.0,
  F_net: 0.0,
  N: 0.0,
  is_stuck: false,
  has_collision: false,
  collision_timer: 0.0,
  x_eq: L0,
  friction_stable_steps: 0,
  _prev_friction: 0.0,
  history_t: new CircularBuffer(50000),
  history_x: new CircularBuffer(50000),
};

function computeSpringForce(x, k) {
  return -k * (x - L0);
}

function physicsStep(state, params, dt) {
  const { x, v } = state;
  const { k, m, v_belt, mu_k, mu_s } = params;

  const F_spring = computeSpringForce(x, k);
  const N = m * G;
  const rel_v = v - v_belt;

  let new_v, new_x, F_friction, is_stuck;

  if (Math.abs(rel_v) < EPS_V) {
    if (Math.abs(F_spring) <= mu_s * N) {
      new_v = v_belt;
      new_x = x + v_belt * dt;
      F_friction = -F_spring;
      is_stuck = true;
    } else {
      F_friction = -mu_k * N * Math.sign(F_spring);
      const F_net = F_spring + F_friction;
      const a = F_net / m;
      new_v = v + a * dt;
      new_x = x + new_v * dt;
      is_stuck = false;
    }
  } else {
    F_friction = -mu_k * N * Math.sign(rel_v);
    const F_net = F_spring + F_friction;
    const a = F_net / m;
    new_v = v + a * dt;
    new_x = x + new_v * dt;

    if (rel_v * (new_v - v_belt) <= 0) {
      if (Math.abs(F_spring) <= mu_s * N) {
        new_v = v_belt;
        new_x = x + v_belt * dt;
        F_friction = -F_spring;
        is_stuck = true;
      } else {
        is_stuck = false;
      }
    } else {
      is_stuck = false;
    }
  }

  const F_net = F_spring + F_friction;

  // Wall collision
  const min_x = BLOCK_W / 2;
  if (new_x < min_x) {
    new_x = min_x;
    new_v = 0.0;
    state.has_collision = true;
    state.collision_timer = 1.5;
  }

  // Equilibrium position
  state.x_eq = L0 - mu_k * N * Math.sign(rel_v) / k;

  // Update state
  state.x = new_x;
  state.v = new_v;
  state.t += dt;
  state.F_spring = F_spring;
  state.F_friction = F_friction;
  state.F_net = F_net;
  state.N = N;
  state.is_stuck = is_stuck;
  state.history_t.push(state.t);
  state.history_x.push(new_x);

  // SHM detection: track friction stability
  if (is_stuck) {
    state.friction_stable_steps = 0;
    state._prev_friction = 0.0;
  } else {
    if (Math.abs(F_friction - state._prev_friction) < 1e-6) {
      state.friction_stable_steps++;
    } else {
      state.friction_stable_steps = 1;
    }
    state._prev_friction = F_friction;
  }
}

function physicsReset(state) {
  state.x = BLOCK_W / 2;
  state.v = 0.0;
  state.t = 0.0;
  state.F_spring = 0.0;
  state.F_friction = 0.0;
  state.F_net = 0.0;
  state.N = 0.0;
  state.is_stuck = false;
  state.has_collision = false;
  state.collision_timer = 0.0;
  state.x_eq = L0;
  state.friction_stable_steps = 0;
  state._prev_friction = 0.0;
  state.history_t.clear();
  state.history_x.clear();
}
