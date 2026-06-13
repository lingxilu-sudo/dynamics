"""
visualization.py — 可视化渲染
物理场景绘制 + 力箭头 + X-T 图更新
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

from physics import PhysicsState, PhysicsParams, L0

# ---- 配色 (霓虹深色主题) ----
C_BG = '#1A1A2E'
C_BG_PLOT = '#0F0F23'
C_WALL_FILL = '#16213E'
C_WALL_EDGE = '#0F3460'
C_BELT = '#4A4A6A'
C_BELT_STRIPE = '#5A5A8A'
C_SPRING = '#00D2FF'
C_BLOCK = '#7D26CD'
C_BLOCK_EDGE = '#FFFFFF'
C_FORCE_SPRING = '#FF3366'
C_FORCE_FRICTION = '#00D2FF'
C_FORCE_NET = '#00FF88'
C_GRID = '#8888AA'
C_LABEL = '#CCCCDD'
C_GRAVITY = '#FF8800'
C_NORMAL = '#FFD700'

# ---- 场景几何参数 ----
SCENE_X_MIN = -0.5
SCENE_X_MAX = 9.0
SCENE_Y_MIN = -0.5
SCENE_Y_MAX = 3.5
WALL_X = 0.0
WALL_H = 3.2
WALL_W = 0.3
BELT_Y0 = 0.3
BELT_H = 0.4
BLOCK_W = 0.12
BLOCK_H = 1.0
ROLLER_R = 0.28
N_SPRING_COILS = 12  # 弹簧线圈数

# 力箭头缩放
FORCE_SCALE = 0.8  # 每牛顿对应多少个场景单位


class SceneRenderer:
    """物理场景渲染器"""

    def __init__(self, ax):
        self.ax = ax
        self._setup_scene()

        # ---- 静态元素 (只创建一次) ----
        # 墙壁
        self.wall = FancyBboxPatch(
            (WALL_X, 0), WALL_W, WALL_H,
            boxstyle="round,pad=0.02",
            facecolor=C_WALL_FILL, edgecolor=C_WALL_EDGE, linewidth=2.5,
            zorder=5
        )
        ax.add_patch(self.wall)

        # 传送带主体
        belt_x = WALL_X + WALL_W + 0.1
        belt_w = SCENE_X_MAX - belt_x + 0.1
        self.belt = FancyBboxPatch(
            (belt_x, BELT_Y0), belt_w, BELT_H,
            boxstyle="round,pad=0.02",
            facecolor=C_BELT, edgecolor='#5A5A8A', linewidth=1,
            zorder=2
        )
        ax.add_patch(self.belt)

        # 滚轮 (左侧)
        self.roller_l = plt.Circle(
            (belt_x, BELT_Y0 + BELT_H / 2), ROLLER_R,
            facecolor='#3A3A5A', edgecolor=C_BELT_STRIPE, linewidth=2,
            zorder=3
        )
        ax.add_patch(self.roller_l)

        # 滚轮 (右侧)
        self.roller_r = plt.Circle(
            (belt_x + belt_w, BELT_Y0 + BELT_H / 2), ROLLER_R,
            facecolor='#3A3A5A', edgecolor=C_BELT_STRIPE, linewidth=2,
            zorder=3
        )
        ax.add_patch(self.roller_r)

        # 滚轮中心点
        self.roller_dot_l = plt.Circle(
            (belt_x, BELT_Y0 + BELT_H / 2), 0.04,
            facecolor=C_BELT_STRIPE, zorder=4
        )
        ax.add_patch(self.roller_dot_l)
        self.roller_dot_r = plt.Circle(
            (belt_x + belt_w, BELT_Y0 + BELT_H / 2), 0.04,
            facecolor=C_BELT_STRIPE, zorder=4
        )
        ax.add_patch(self.roller_dot_r)

        # 传送带动态条纹列表
        self.belt_stripes = []

        # ---- 平衡位置标记（合力为0，动态更新）----
        eq_x = WALL_X + WALL_W + L0  # 初始位置
        eq_y0 = BELT_Y0 - 0.2
        eq_y1 = BELT_Y0 + BELT_H + BLOCK_H + 0.4
        self.eq_line = ax.plot(
            [eq_x, eq_x], [eq_y0, eq_y1],
            '--', color='#00FF88', linewidth=1.5, alpha=0.6, zorder=3
        )[0]
        self.eq_label = ax.text(
            eq_x + 0.05, eq_y1 + 0.05, '',
            fontsize=7, color='#00FF88', va='bottom', ha='left', zorder=20
        )

        # ---- 弹簧原长标记（固定，x = L₀）----
        l0_x = WALL_X + WALL_W + L0
        l0_y0 = BELT_Y0 - 0.2
        l0_y1 = BELT_Y0 + BELT_H + BLOCK_H + 0.4
        self.l0_line = ax.plot(
            [l0_x, l0_x], [l0_y0, l0_y1],
            '-.', color='#999999', linewidth=1.0, alpha=0.5, zorder=3
        )[0]
        self.l0_label = ax.text(
            l0_x + 0.05, l0_y1 + 0.05, f'弹簧原长\nL₀={L0:.1f}',
            fontsize=7, color='#999999', va='bottom', ha='left', zorder=20
        )

        # ---- 传送带 x 轴刻度 ----（物理坐标 x，原点=墙壁右边缘）
        belt_x0 = WALL_X + WALL_W + 0.1
        belt_w = SCENE_X_MAX - belt_x0 + 0.1
        tick_y = BELT_Y0 - 0.15
        n_ticks = 8
        for i in range(n_ticks + 1):
            tx = belt_x0 + belt_w * i / n_ticks
            ax.plot([tx, tx], [tick_y, tick_y + 0.08],
                    color=C_GRID, linewidth=1, alpha=0.5, zorder=3)
            ax.text(tx, tick_y - 0.08, f'{belt_w * i / n_ticks:.1f}',
                    fontsize=6, color=C_GRID, ha='center', va='top', zorder=20)

        # ---- 动态元素 (每帧更新) ----
        # 弹簧 (Line2D) — 灰色螺旋
        self.spring_line = ax.plot([], [], color='#AAAAAA', linewidth=2.0,
                                   alpha=0.9, zorder=6)[0]

        # 弹簧发光效果 (第二条粗线)
        self.spring_glow = ax.plot([], [], color='#AAAAAA', linewidth=5,
                                   alpha=0.15, zorder=5)[0]

        # 方块
        self.block = FancyBboxPatch(
            (0, BELT_Y0 + BELT_H - 0.02), BLOCK_W, BLOCK_H,
            boxstyle="round,pad=0.05",
            facecolor=C_BLOCK, edgecolor=C_BLOCK_EDGE, linewidth=2,
            zorder=7
        )
        ax.add_patch(self.block)

        # 方块标签
        self.block_label = ax.text(0, 0, '', fontsize=9, color='#FFFFFF',
                                    ha='center', va='center', fontweight='bold',
                                    zorder=8)

        # 粘滞状态指示
        self.stuck_indicator = ax.text(0, 0, '', fontsize=8,
                                        color=C_FORCE_NET, ha='center',
                                        va='bottom', fontstyle='italic')

        # 碰撞提示
        self.collision_text = ax.text(
            SCENE_X_MAX / 2, SCENE_Y_MAX - 0.4, '',
            fontsize=14, color='#FF4444', ha='center', va='top',
            fontweight='bold', zorder=30, alpha=0
        )

        # ---- 力箭头 (创建空箭头, 每帧更新) ----
        self.arrows = {}
        for key, color, label in [
            ('F_spring', C_FORCE_SPRING, r'$F_{spring}$'),
            ('F_friction', C_FORCE_FRICTION, r'$F_{friction}$'),
            ('F_net', C_FORCE_NET, r'$F_{net}$'),
        ]:
            arr = FancyArrowPatch(
                (0, 0), (0, 0),
                arrowstyle='->,head_width=0.3,head_length=0.4',
                color=color, linewidth=2.5, zorder=10,
                mutation_scale=20,
            )
            ax.add_patch(arr)
            self.arrows[key] = arr

        # 重力/支持力箭头 (mutation_scale 更大确保箭头头可见)
        for key, color in [('gravity', C_GRAVITY), ('normal', C_NORMAL)]:
            arr = FancyArrowPatch(
                (0, 0), (0, 0),
                arrowstyle='->,head_width=0.3,head_length=0.35',
                color=color, linewidth=2.5, zorder=9,
                mutation_scale=20,
            )
            ax.add_patch(arr)
            self.arrows[key] = arr

        # 力标签图例
        self._create_legend()

    def _setup_scene(self):
        self.ax.set_xlim(SCENE_X_MIN, SCENE_X_MAX)
        self.ax.set_ylim(SCENE_Y_MIN, SCENE_Y_MAX)
        self.ax.set_facecolor(C_BG)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

    def _create_legend(self):
        """在场景左上角创建受力图例"""
        legend_y = 3.0
        x_start = 6.5
        items = [
            (C_FORCE_SPRING, r'$F_{spring}$', '弹簧力'),
            (C_FORCE_FRICTION, r'$F_{friction}$', '摩擦力'),
            (C_FORCE_NET, r'$F_{net}$', '合力'),
            (C_GRAVITY, r'$mg$', '重力'),
            (C_NORMAL, r'$N$', '支持力'),
        ]
        for i, (color, label, desc) in enumerate(items):
            y = legend_y - i * 0.35
            self.ax.plot([x_start, x_start + 0.3], [y, y],
                         color=color, linewidth=2.5, zorder=20)
            self.ax.text(x_start + 0.4, y, f'{label} ({desc})',
                         fontsize=7.5, color=C_LABEL, va='center', zorder=20)

    def update(self, state: PhysicsState, params: PhysicsParams):
        """更新所有动态元素"""
        x = state.x  # x = 方块中心距墙壁右边缘的距离
        block_center_x = WALL_X + WALL_W + x  # 方块中心在场景中的X坐标
        block_left = block_center_x - BLOCK_W / 2  # 方块左边缘

        # ---- 弹簧 ----
        spring_x0 = WALL_X + WALL_W
        spring_x1 = block_left  # 弹簧连接方块左边缘
        spring_y = BELT_Y0 + BELT_H + BLOCK_H * 0.5  # 弹簧连接方块侧面中部
        spring_len = max(spring_x1 - spring_x0, 0.05)
        # 确保弹簧始终可见（最小长度下也画出来）
        coil_n = max(4, int(N_SPRING_COILS * spring_len / L0))
        n_pts = max(9, coil_n * 4 + 1)  # 每线圈4点形成锯齿
        amplitude = min(0.22, max(0.06, 0.18 * spring_len / L0))
        # 锯齿波模拟螺旋线圈
        t = np.linspace(0, 1, n_pts)
        xs = spring_x0 + spring_len * t
        # 锯齿波: 每个周期 4 段 — 上升、水平、下降、水平
        phase = (coil_n * t) % 1.0
        saw = np.where(phase < 0.25, 4 * phase,           # 上升
                np.where(phase < 0.50, 2 - 4 * phase,     # 下降
                np.where(phase < 0.75, 4 * phase - 2,     # 上升
                        4 - 4 * phase)))                   # 下降
        ys = spring_y + amplitude * saw
        xs[0] = spring_x0
        xs[-1] = spring_x1
        ys[0] = spring_y
        ys[-1] = spring_y
        self.spring_line.set_data(xs, ys)
        self.spring_glow.set_data(xs, ys)

        # ---- 方块 ----
        block_x = block_left
        block_y = BELT_Y0 + BELT_H  # 方块坐在传送带上表面
        self.block.set_x(block_x)
        self.block.set_y(block_y)
        # 方块标签 (显示速度，位于方块中心)
        speed_text = f'v={state.v:.2f}'
        self.block_label.set_text(speed_text)
        self.block_label.set_x(block_x + BLOCK_W / 2)
        self.block_label.set_y(block_y + BLOCK_H / 2)

        # ---- 粘滞指示 ----
        self.stuck_indicator.set_text('粘滞' if state.is_stuck else '滑动')
        self.stuck_indicator.set_x(block_x + BLOCK_W / 2)
        self.stuck_indicator.set_y(block_y + BLOCK_H + 0.15)

        # ---- 传送带条纹 (动态绘制) ----
        for s in self.belt_stripes:
            s.remove()
        self.belt_stripes.clear()

        belt_x0 = WALL_X + WALL_W + 0.1
        belt_w = SCENE_X_MAX - belt_x0 + 0.1
        belt_y = BELT_Y0
        n_stripes = 10
        stripe_spacing = belt_w / n_stripes
        shift = (state.t * params.v_belt) % stripe_spacing
        for i in range(n_stripes + 3):
            sx = belt_x0 + stripe_spacing * i + shift
            while sx > belt_x0 + belt_w:
                sx -= belt_w + stripe_spacing
            while sx < belt_x0 - stripe_spacing:
                sx += belt_w + stripe_spacing
            if belt_x0 - stripe_spacing <= sx <= belt_x0 + belt_w + stripe_spacing:
                stripe = mlines.Line2D(
                    [sx, sx], [belt_y, belt_y + BELT_H],
                    color=C_BELT_STRIPE, linewidth=2, alpha=0.7, zorder=2
                )
                self.ax.add_line(stripe)
                self.belt_stripes.append(stripe)

        # ---- 平衡位置标记（动态更新）----
        eq_scene_x = WALL_X + WALL_W + state.x_eq
        eq_y0 = BELT_Y0 - 0.2
        eq_y1 = BELT_Y0 + BELT_H + BLOCK_H + 0.4
        self.eq_line.set_data([eq_scene_x, eq_scene_x], [eq_y0, eq_y1])
        self.eq_label.set_x(eq_scene_x + 0.05)
        self.eq_label.set_text(f'平衡位置\nx_eq={state.x_eq:.2f}')

        # ---- 碰撞提示 ----
        if state.has_collision and state.collision_timer > 0:
            self.collision_text.set_text('Perfectly Inelastic Collision!')
            self.collision_text.set_alpha(min(1.0, state.collision_timer))
            state.collision_timer -= 1.0 / 60  # 60fps下逐帧衰减
            if state.collision_timer <= 0:
                state.has_collision = False
        else:
            self.collision_text.set_alpha(0)

        # ---- 力箭头 ----
        self._update_force_arrows(state, block_x, block_y)

    def _update_force_arrows(self, state: PhysicsState, bx, by):
        """更新力箭头位置和大小，所有箭头均从方块中心出发"""
        cx = bx + BLOCK_W / 2   # 方块中心 X
        cy = by + BLOCK_H / 2   # 方块中心 Y

        # ---- 水平力缩放 ----
        max_f_h = max(abs(state.F_spring), abs(state.F_friction), abs(state.F_net), 0.01)
        scale_h = min(2.5, max(0.3, 1.2 / (max_f_h / 10 + 1)))

        # ---- 水平方向（从方块中心向左右延伸）----
        # 弹力：向左（负方向）
        self._set_arrow('F_spring', cx, cy, cx - abs(state.F_spring) * scale_h, cy, C_FORCE_SPRING)

        # 摩擦力：向右或向左（取决于相对速度方向）
        fx = cx + state.F_friction * scale_h
        self._set_arrow('F_friction', cx, cy, fx, cy, C_FORCE_FRICTION)

        # 合力：向右或向左
        net_x = cx + state.F_net * scale_h
        self._set_arrow('F_net', cx, cy, net_x, cy, C_FORCE_NET)

        # ---- 竖直方向（固定缩放，防止箭头过长）----
        scale_v = 0.08  # 固定缩放：N≈9.81 → 长度约0.78，在场景内合理

        # 重力：向下
        self._set_arrow('gravity', cx, cy, cx, cy - state.N * scale_v, C_GRAVITY)

        # 支持力：向上
        self._set_arrow('normal', cx, cy, cx, cy + state.N * scale_v, C_NORMAL)

    def _set_arrow(self, key, x1, y1, x2, y2, color):
        """设置箭头位置，如果不存在则创建"""
        if key not in self.arrows:
            arr = FancyArrowPatch(
                (0, 0), (0, 0),
                arrowstyle='->,head_width=0.2,head_length=0.25',
                color=color, linewidth=2.5, zorder=9,
                mutation_scale=15,
            )
            self.ax.add_patch(arr)
            self.arrows[key] = arr

        self.arrows[key].set_positions((x1, y1), (x2, y2))


class XTPlotter:
    """X-T 图绘制器"""

    def __init__(self, ax):
        self.ax = ax
        self._setup()

        self.line = ax.plot([], [], color=C_FORCE_FRICTION, linewidth=2,
                            alpha=0.9, zorder=5)[0]
        # 发光效果
        self.glow = ax.plot([], [], color=C_FORCE_FRICTION, linewidth=5,
                            alpha=0.15, zorder=4)[0]
        self.max_points = 5000  # 增大容量，保留更多数据

    def _setup(self):
        ax = self.ax
        ax.set_facecolor(C_BG_PLOT)
        ax.set_xlabel('t (s)', color=C_LABEL, fontsize=9)
        ax.set_ylabel('x (m)', color=C_LABEL, fontsize=9)
        ax.tick_params(colors=C_GRID, labelsize=8)
        ax.grid(True, alpha=0.15, color=C_GRID, linestyle='--')
        ax.set_xlim(0, 100)
        ax.set_ylim(0.5, 4.0)
        for spine in ax.spines.values():
            spine.set_color(C_GRID)
            spine.set_alpha(0.5)
        # 平衡位置水平线（动态更新）
        self.eq_hline = ax.axhline(
            y=L0, color='#00FF88', linewidth=1.2,
            linestyle='--', alpha=0.6, zorder=4
        )
        self.eq_text = ax.text(
            0.02, 0.95, '', transform=ax.transAxes,
            fontsize=8, color='#00FF88', va='top', ha='left',
            alpha=0.8
        )

    def update(self, times, positions, x_eq: float = L0):
        """更新曲线数据，滚动时间窗口（最近100秒）"""
        if len(times) < 2:
            return

        t_data = list(times)
        x_data = list(positions)

        # 当前时间
        t_now = t_data[-1]
        t_start = max(0, t_now - 100)

        # 只保留最近100秒的数据用于显示
        # 找到起始索引
        idx = 0
        for i, tv in enumerate(t_data):
            if tv >= t_start:
                idx = i
                break

        t_show = t_data[idx:]
        x_show = x_data[idx:]

        self.line.set_data(t_show, x_show)
        self.glow.set_data(t_show, x_show)

        # 更新平衡位置水平线
        self.eq_hline.set_ydata([x_eq, x_eq])
        self.eq_text.set_text(f'x_eq = {x_eq:.2f}')

        # 滚动时间轴：窗口 [t_start, t_start+100]
        self.ax.set_xlim(t_start, t_start + 100)
        # Y 轴固定范围
        self.ax.set_ylim(0.5, 4.0)
