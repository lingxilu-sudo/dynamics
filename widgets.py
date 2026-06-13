"""
widgets.py — 交互控件
滑块 (k, mu_k, ratio, v_belt, m) 和按钮 (play/pause/reset)
"""

from matplotlib.widgets import Slider, Button
from physics import PhysicsParams, PhysicsState, reset

# ---- 霓虹深色配色 (控件) ----
C_BG = '#1A1A2E'
C_SLIDER = '#00D2FF'
C_SLIDER_TRACK = '#3A3A5A'
C_LABEL = '#CCCCDD'
C_BTN_PLAY = '#B399FF'
C_BTN_PAUSE = '#003153'
C_BTN_RESET = '#9B30FF'

# ---- 参数范围 ----
PARAM_RANGES = {
    'k': (0.5, 20.0),
    'mu_k': (0.05, 1.0),
    'ratio': (1.0, 3.0),
    'v_belt': (0.2, 3.0),
    'm': (0.2, 5.0),
}

PARAM_INIT = {
    'k': 3.0,
    'mu_k': 0.25,
    'ratio': 1.6,
    'v_belt': 1.5,
    'm': 1.0,
}

PARAM_LABELS = {
    'k': r'$k$ (N/m)',
    'mu_k': r'$\mu_k$',
    'ratio': r'$\mu_s / \mu_k$',
    'v_belt': r'$v_{belt}$ (m/s)',
    'm': r'$m$ (kg)',
}


class ControlPanel:
    """控制面板: 滑块 + 按钮"""

    def __init__(self, fig, params: PhysicsParams, state: PhysicsState):
        self.params = params
        self.state = state
        self.is_playing = True

        # 在 figure 右侧底部区域创建子坐标轴
        self.axes = {}
        self.sliders = {}

        # 5 个滑块 + 3 个按钮 = 8 行
        n_rows = 8
        row_h = 0.035
        start_y = 0.12
        x0, xw = 0.72, 0.25

        # ---- 标题 ----
        self.title_ax = fig.add_axes([x0, start_y + n_rows * row_h + 0.02, xw, 0.04])
        self.title_ax.axis('off')
        self.title_text = self.title_ax.text(
            0.5, 0.5, '控制面板', fontsize=11, fontweight='bold',
            color=C_LABEL, ha='center', va='center'
        )

        # ---- 滑块 ----
        keys = ['k', 'mu_k', 'ratio', 'v_belt', 'm']
        for i, key in enumerate(keys):
            y = start_y + (n_rows - 1 - i) * row_h
            ax = fig.add_axes([x0, y, xw, row_h * 0.8])
            slider = Slider(
                ax=ax, label=PARAM_LABELS[key],
                valmin=PARAM_RANGES[key][0],
                valmax=PARAM_RANGES[key][1],
                valinit=PARAM_INIT[key],
                color=C_SLIDER,
                track_color=C_SLIDER_TRACK,
                valfmt='%.2f',
            )
            # 样式调整
            slider.label.set_color(C_LABEL)
            slider.label.set_fontsize(8)
            slider.valtext.set_color(C_LABEL)
            slider.valtext.set_fontsize(8)
            slider.poly.set_facecolor(C_SLIDER)

            # 绑定回调
            key_callback = key
            slider.on_changed(lambda val, k=key_callback: self._on_slider_change(k, val))

            self.axes[key] = ax
            self.sliders[key] = slider

        # ---- 按钮 ----
        btn_w = 0.07
        btn_h = 0.04
        btn_y = start_y - 0.01
        btn_x_center = x0 + xw / 2

        # 播放
        self.btn_play_ax = fig.add_axes(
            [btn_x_center - btn_w - 0.06, btn_y, btn_w, btn_h])
        self.btn_play = Button(self.btn_play_ax, '▶')
        self.btn_play.label.set_fontsize(10)
        self.btn_play.label.set_color('#1A1A2E')
        self.btn_play.ax.set_facecolor(C_BTN_PLAY)
        self.btn_play.on_clicked(self._on_play)

        # 暂停
        self.btn_pause_ax = fig.add_axes(
            [btn_x_center, btn_y, btn_w-0.03, btn_h])
        self.btn_pause = Button(self.btn_pause_ax, '⏸')
        self.btn_pause.label.set_fontsize(10)
        self.btn_pause.label.set_color('#FFFFFF')
        self.btn_pause.ax.set_facecolor(C_BTN_PAUSE)
        self.btn_pause.on_clicked(self._on_pause)

        # 重置
        self.btn_reset_ax = fig.add_axes(
            [btn_x_center + btn_w , btn_y, btn_w, btn_h])
        self.btn_reset = Button(self.btn_reset_ax, '↺')
        self.btn_reset.label.set_fontsize(10)
        self.btn_reset.label.set_color('#FFFFFF')
        self.btn_reset.ax.set_facecolor(C_BTN_RESET)
        self.btn_reset.on_clicked(self._on_reset)

    def _on_slider_change(self, key, val):
        setattr(self.params, key, val)

    def _on_play(self, event):
        self.is_playing = True

    def _on_pause(self, event):
        self.is_playing = False

    def _on_reset(self, event):
        reset(self.state)
        self.is_playing = True
