"""
widgets.py — 交互控件
滑块 (k, mu_k, ratio, v_belt, m) 和按钮 (play/pause/reset)
"""

from matplotlib.widgets import Slider, Button
from physics import PhysicsParams, PhysicsState, reset

# ---- 霍虹深色配色 (控件) ----
C_BG = '#1A1A2E'
C_SLIDER = '#00D2FF'
C_SLIDER_TRACK = '#3A3A5A'
C_LABEL = '#CCCCDD'
C_BTN = '#00D2FF'           # 荧光蓝按钮背景
C_BTN_ACTIVE = '#00FFFF'    # 高亮荧光蓝（选中态）
C_BTN_TEXT = '#000000'      # 按钮文字黑色

# ---- 参数范围 ----
PARAM_RANGES = {
    'k': (0.5, 20.0),
    'mu_k': (0.0, 1.0),
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
    'k': 'k (N/m)',
    'mu_k': 'mu_k',
    'ratio': 'mu_s / mu_k',
    'v_belt': 'v_belt (m/s)',
    'm': 'm (kg)',
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
        row_h = 0.032
        start_y = 0.08
        x0, xw = 0.76, 0.21

        # ---- 标题 ----
        self.title_ax = fig.add_axes([x0, start_y + n_rows * row_h + 0.02, xw, 0.04])
        self.title_ax.axis('off')
        self.title_text = self.title_ax.text(
            0.5, 0.5, 'Control Panel', fontsize=11, fontweight='bold',
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
        btn_size = 0.05  # 正方形按钮尺寸
        btn_y = start_y - 0.02
        btn_gap = 0.02  # 按钮间距
        total_btn_w = 3 * btn_size + 2 * btn_gap
        btn_x_start = x0 + (xw - total_btn_w) / 2  # 居中对齐

        # 播放
        self.btn_play_ax = fig.add_axes(
            [btn_x_start, btn_y, btn_size, btn_size])
        self.btn_play = Button(self.btn_play_ax, 'Play')
        self.btn_play.label.set_fontsize(9)
        self.btn_play.label.set_color(C_BTN_TEXT)
        self.btn_play.label.set_fontweight('bold')
        self.btn_play.ax.set_facecolor(C_BTN)
        self.btn_play.on_clicked(self._on_play)

        # 暂停
        self.btn_pause_ax = fig.add_axes(
            [btn_x_start + btn_size + btn_gap, btn_y, btn_size, btn_size])
        self.btn_pause = Button(self.btn_pause_ax, 'Pause')
        self.btn_pause.label.set_fontsize(8)
        self.btn_pause.label.set_color(C_BTN_TEXT)
        self.btn_pause.label.set_fontweight('bold')
        self.btn_pause.ax.set_facecolor(C_BTN)
        self.btn_pause.on_clicked(self._on_pause)

        # 重置
        self.btn_reset_ax = fig.add_axes(
            [btn_x_start + 2 * (btn_size + btn_gap), btn_y, btn_size, btn_size])
        self.btn_reset = Button(self.btn_reset_ax, 'Reset')
        self.btn_reset.label.set_fontsize(8)
        self.btn_reset.label.set_color(C_BTN_TEXT)
        self.btn_reset.label.set_fontweight('bold')
        self.btn_reset.ax.set_facecolor(C_BTN)
        self.btn_reset.on_clicked(self._on_reset)

        # ---- 速度倍率按钮 ----
        self.speed_multiplier = 1
        speed_options = [1, 2, 5, 10]
        speed_btn_size = 0.04
        speed_btn_gap = 0.015
        speed_row_y = btn_y - speed_btn_size - 0.02
        total_speed_w = len(speed_options) * speed_btn_size + (len(speed_options) - 1) * speed_btn_gap
        speed_x_start = x0 + (xw - total_speed_w) / 2

        # 速度标题
        self.speed_label_ax = fig.add_axes([x0, speed_row_y + speed_btn_size + 0.005, xw, 0.02])
        self.speed_label_ax.axis('off')
        self.speed_label_ax.text(
            0.5, 0.5, 'Speed', fontsize=9, color=C_LABEL,
            ha='center', va='center'
        )

        self.speed_btns = []
        self.speed_btn_axes = []
        for i, spd in enumerate(speed_options):
            sx = speed_x_start + i * (speed_btn_size + speed_btn_gap)
            ax_spd = fig.add_axes([sx, speed_row_y, speed_btn_size, speed_btn_size])
            btn = Button(ax_spd, f'{spd}x')
            btn.label.set_fontsize(8)
            btn.label.set_fontweight('bold')
            btn.label.set_color(C_BTN_TEXT)
            if spd == 1:
                ax_spd.set_facecolor(C_BTN_ACTIVE)
            else:
                ax_spd.set_facecolor(C_BTN)
            btn.on_clicked(lambda event, s=spd: self._on_speed(s))
            self.speed_btns.append(btn)
            self.speed_btn_axes.append(ax_spd)
        self._speed_options = speed_options

    def _on_slider_change(self, key, val):
        setattr(self.params, key, val)

    def _on_play(self, event):
        self.is_playing = True

    def _on_pause(self, event):
        self.is_playing = False

    def _on_reset(self, event):
        reset(self.state)
        self.is_playing = True

    def _on_speed(self, spd):
        self.speed_multiplier = spd
        # 更新按钮外观：高亮当前选中的倍率
        for i, s in enumerate(self._speed_options):
            if s == spd:
                self.speed_btn_axes[i].set_facecolor(C_BTN_ACTIVE)
            else:
                self.speed_btn_axes[i].set_facecolor(C_BTN)
