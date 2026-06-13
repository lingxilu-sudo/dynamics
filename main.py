"""
main.py — 程序入口
GridSpec 布局管理, FuncAnimation 动画循环, 编排物理-可视化-控制
"""

import matplotlib
matplotlib.use('TkAgg')  # 交互式后端, 确保滑块/按钮可用

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.animation import FuncAnimation

from physics import PhysicsState, PhysicsParams, step, DT_PHYS
from visualization import SceneRenderer, XTPlotter
from widgets import ControlPanel

# ---- 全局配置 ----
C_BG = '#1A1A2E'
FPS = 60
SUBSTEPS = 12  # 每帧物理子步数 (加快仿真速度)


def animate(frame, state, params, renderer, xt_plotter, ctrl):
    """每帧更新"""
    # 物理步进
    if ctrl.is_playing:
        for _ in range(SUBSTEPS):
            step(state, params, DT_PHYS)

    # 渲染场景
    renderer.update(state, params)

    # 更新 X-T 图 (保留完整历史，不截断)
    if len(state.history_t) > 1:
        xt_plotter.update(state.history_t, state.history_x, state.x_eq)

    # 不返回列表 (blit=False, 全部重绘)
    return []


def main():
    # ---- 创建图形和布局 ----
    fig = plt.figure(figsize=(14, 8), facecolor=C_BG)
    fig.canvas.manager.set_window_title('传送带弹簧振子模拟')

    gs = GridSpec(
        2, 2, figure=fig,
        height_ratios=[7, 3],
        width_ratios=[7, 3],
        hspace=0.12, wspace=0.12,
        left=0.02, right=0.98, top=0.97, bottom=0.03
    )

    # 场景 (上: 横跨两列)
    ax_scene = fig.add_subplot(gs[0, :])

    # X-T 图 (下左)
    ax_xt = fig.add_subplot(gs[1, 0])

    # ---- 初始化物理 ----
    params = PhysicsParams()
    state = PhysicsState()

    # ---- 初始化渲染器 ----
    renderer = SceneRenderer(ax_scene)
    xt_plotter = XTPlotter(ax_xt)

    # ---- 初始化控件 ----
    ctrl = ControlPanel(fig, params, state)

    # ---- 启动动画 ----
    ani = FuncAnimation(
        fig, animate,
        fargs=(state, params, renderer, xt_plotter, ctrl),
        interval=1000 // FPS,
        blit=False,  # 关闭 blit 确保所有元素正确重绘
        cache_frame_data=False,
    )

    plt.show()
    return ani


if __name__ == '__main__':
    ani = main()
