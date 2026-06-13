"""
physics.py — 物理引擎
传送带上的弹簧-质量块系统，支持静摩擦/动摩擦 stick-slip 切换。
"""

import numpy as np
from collections import deque
from typing import Deque
from dataclasses import dataclass, field

# ---- 物理常量 ----
G = 9.81          # 重力加速度 (m/s²)
L0 = 1.5          # 弹簧自然长度 (场景坐标单位)
WALL_W = 0.3      # 墙壁宽度 (m)
BLOCK_W = 0.12    # 方块宽度 (m)
EPS_V = 1e-6      # 速度判零阈值
DT_PHYS = 0.0008  # 物理积分步长 (s)


@dataclass
class PhysicsParams:
    """可调物理参数"""
    k: float = 3.0        # 弹簧劲度系数 (N/m) — 降低以增大振幅
    mu_k: float = 0.25    # 动摩擦系数
    ratio: float = 1.6    # 静摩擦倍数: mu_s = ratio * mu_k
    v_belt: float = 1.5   # 传送带速度 (m/s, 正=向右)
    m: float = 1.0        # 方块质量 (kg)

    @property
    def mu_s(self) -> float:
        return self.ratio * self.mu_k


@dataclass
class PhysicsState:
    """物理系统状态"""
    x: float = BLOCK_W / 2        # 方块中心距墙壁右边缘的距离 (m)
    v: float = 0.0              # 方块速度 (m/s)
    t: float = 0.0              # 仿真时间 (s)
    F_spring: float = 0.0       # 弹簧力 (N, 用于显示)
    F_friction: float = 0.0     # 摩擦力 (N, 用于显示)
    F_net: float = 0.0          # 合力 (N, 用于显示)
    N: float = 0.0              # 支持力 (N, 用于显示)
    is_stuck: bool = False      # 是否处于静摩擦粘滞状态
    has_collision: bool = False  # 是否发生墙壁碰撞（本帧）
    collision_timer: float = 0.0  # 碰撞提示显示计时器
    x_eq: float = L0            # 动态平衡位置（合力为0的位置）
    # SHM 判定：连续多步摩擦力恒定（方向+大小不变）
    friction_stable_steps: int = 0
    _prev_friction: float = 0.0
    history_x: Deque[float] = field(default_factory=lambda: deque(maxlen=50000))
    history_t: Deque[float] = field(default_factory=lambda: deque(maxlen=50000))


def compute_spring_force(x: float, k: float) -> float:
    """计算弹簧力 (Hooke's Law): F = -k * (x - L0)"""
    return -k * (x - L0)


def step(state: PhysicsState, params: PhysicsParams, dt: float = DT_PHYS):
    """推进物理仿真一步 (含 stick-slip 切换)"""
    x, v = state.x, state.v
    k, m = params.k, params.m
    v_belt = params.v_belt
    mu_k, mu_s = params.mu_k, params.mu_s

    # 弹簧力
    F_spring = compute_spring_force(x, k)

    # 支持力 (始终等于重力)
    N = m * G

    rel_v = v - v_belt  # 相对传送带的速度

    # ---- 判定并计算摩擦力 ----
    if abs(rel_v) < EPS_V:
        # 相对速度 ≈ 0 → 可能处于粘滞状态
        if abs(F_spring) <= mu_s * N:
            # 静摩擦足够 → 粘滞: 方块随传送带运动
            new_v = v_belt
            new_x = x + v_belt * dt
            F_friction = -F_spring  # 摩擦力精确平衡弹簧力
            is_stuck = True
        else:
            # 弹簧力超过最大静摩擦 → 开始滑动
            # 滑动方向由弹簧力方向决定: 弹簧向左拉则相对向左滑
            slip_dir = -np.sign(F_spring)  # 弹簧向左(F_spring<0)→滑动方向向左(slip_dir=-1)
            F_friction = mu_k * N * slip_dir  # 摩擦力阻碍滑动
            # 但根据定义 kinetic friction = -mu_k*N*sign(rel_v)
            # 此时 rel_v 与 slip_dir 同号
            F_friction = -mu_k * N * np.sign(F_spring)  # = -mu_k*N*sign(F_spring)
            # 验证: F_spring<0(左拉) → F_friction = +mu_k*N(向右推) ✓
            F_net = F_spring + F_friction
            a = F_net / m
            new_v = v + a * dt
            new_x = x + new_v * dt
            is_stuck = False
    else:
        # 已有相对滑动 → 动摩擦
        F_friction = -mu_k * N * np.sign(rel_v)
        F_net = F_spring + F_friction
        a = F_net / m
        new_v = v + a * dt
        new_x = x + new_v * dt

        # 检查是否穿越 v_belt (可能重新粘滞)
        if rel_v * (new_v - v_belt) <= 0:
            # 相对速度穿越零
            if abs(F_spring) <= mu_s * N:
                new_v = v_belt
                new_x = x + v_belt * dt
                F_friction = -F_spring
                is_stuck = True
            else:
                is_stuck = False
        else:
            is_stuck = False

    F_net = F_spring + F_friction

    # ---- 墙壁碰撞 (方块左边缘碰到墙壁右边缘) ----
    # x 为方块中心距墙壁右边缘的距离，方块左边缘 = x - BLOCK_W/2
    min_x = BLOCK_W / 2  # 方块左边缘不能进入墙壁
    if new_x < min_x:
        new_x = min_x
        new_v = 0.0  # 完全非弹性碰撞，速度归零
        state.has_collision = True
        state.collision_timer = 1.5  # 提示显示1.5秒

    # ---- 计算动态平衡位置（动摩擦与弹簧力相等的位置）----
    # F_spring + F_friction = 0 → -k*(x_eq - L0) - μ_k*N*sign(rel_v) = 0
    # → x_eq = L0 - μ_k*N*sign(rel_v)/k
    state.x_eq = L0 - mu_k * N * np.sign(rel_v) / k

    # ---- 更新状态 ----
    state.x = new_x
    state.v = new_v
    state.t += dt
    state.F_spring = F_spring
    state.F_friction = F_friction
    state.F_net = F_net
    state.N = N
    state.is_stuck = is_stuck
    state.history_x.append(new_x)
    state.history_t.append(state.t)

    # ---- SHM 判定：追踪摩擦力是否恒定 ----
    if is_stuck:
        # 粘滞状态下摩擦力在变（平衡弹簧力），重置
        state.friction_stable_steps = 0
        state._prev_friction = 0.0
    else:
        # 滑动状态：检查摩擦力是否和上一步一致
        if abs(F_friction - state._prev_friction) < 1e-6:
            state.friction_stable_steps += 1
        else:
            state.friction_stable_steps = 1  # 新的稳定段开始
        state._prev_friction = F_friction


def reset(state: PhysicsState):
    """重置为初始状态"""
    state.x = BLOCK_W / 2  # 方块左边缘贴墙壁右边缘
    state.v = 0.0
    state.t = 0.0
    state.F_spring = 0.0
    state.F_friction = 0.0
    state.F_net = 0.0
    state.N = 0.0
    state.is_stuck = False
    state.x_eq = L0
    state.friction_stable_steps = 0
    state._prev_friction = 0.0
    state.history_x.clear()
    state.history_t.clear()
