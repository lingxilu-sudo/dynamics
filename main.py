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
from visualization import SceneRenderer, XTPlotter, FormulaPanel
from widgets import ControlPanel

# ---- 全局配置 ----
C_BG = '#1A1A2E'
FPS = 60
SUBSTEPS = 12  # 每帧物理子步数 (加快仿真速度)


def animate(frame, state, params, renderer, xt_plotter, formula_panel, ctrl):
    """每帧更新"""
    # 物理步进
    if ctrl.is_playing:
        steps = SUBSTEPS * ctrl.speed_multiplier
        for _ in range(steps):
            step(state, params, DT_PHYS)

    # 渲染场景
    renderer.update(state, params)

    # 更新 X-T 图 (保留完整历史，不截断)
    if len(state.history_t) > 1:
        xt_plotter.update(state.history_t, state.history_x, state.x_eq, state.is_stuck)

    # 更新公式面板
    formula_panel.update(state, params)

    # 不返回列表 (blit=False, 全部重绘)
    return []


def main():
    # ---- 创建图形和布局 ----
    fig = plt.figure(figsize=(16, 9), facecolor=C_BG)
    fig.canvas.manager.set_window_title('传送带弹簧振子模拟')

    gs = GridSpec(
        2, 2, figure=fig,
        height_ratios=[6, 4],
        width_ratios=[7.5, 2.5],
        hspace=0.15, wspace=0.06,
        left=0.03, right=0.97, top=0.96, bottom=0.04
    )

    # 场景 (左上)
    ax_scene = fig.add_subplot(gs[0, 0])

    # 公式面板 (右上)
    ax_formula = fig.add_subplot(gs[0, 1])

    # X-T 图 (左下)
    ax_xt = fig.add_subplot(gs[1, 0])

    # ---- 初始化物理 ----
    params = PhysicsParams()
    state = PhysicsState()

    # ---- 初始化渲染器 ----
    renderer = SceneRenderer(ax_scene)
    xt_plotter = XTPlotter(ax_xt)
    formula_panel = FormulaPanel(ax_formula)

    # ---- 初始化控件 ----
    ctrl = ControlPanel(fig, params, state)

    # ---- 启动动画 ----
    ani = FuncAnimation(
        fig, animate,
        fargs=(state, params, renderer, xt_plotter, formula_panel, ctrl),
        interval=1000 // FPS,
        blit=False,  # 关闭 blit 确保所有元素正确重绘
        cache_frame_data=False,
    )

    # ---- 水印 ----
    fig.text(
        0.5, 0.005, 'github.com/lingxilu-sudo',
        ha='center', va='bottom',
        fontsize=12, fontstyle='italic',
        color='#B399FF', alpha=0.6,
        fontfamily='monospace',
    )

    plt.show()
    return ani


if __name__ == '__main__':
    ani = main()
