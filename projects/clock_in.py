import datetime
import ipywidgets as widgets
from IPython.display import display

def create_session_widgets(log_file="projects/pthread.log"):
    started = False
    ended = False

    # 设置按钮样式：更大尺寸和字体
    btn_style = {'font_size': '20px', 'font_weight': 'bold'}
    start_btn = widgets.Button(
        description='▶ 开始学习',
        button_style='success',
        style=btn_style,
        layout=widgets.Layout(width='150px', height='50px')
    )
    end_btn = widgets.Button(
        description='■ 结束学习',
        button_style='danger',
        style=btn_style,
        layout=widgets.Layout(width='150px', height='50px')
    )
    # 状态标签也加大字号
    status_label = widgets.HTML(value="<b style='font-size:1.5em;'>状态：</b><span style='color:gray; font-size:1.5em;'>未打卡</span>")

    def log_event(event_type):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n#################### 事件分隔 ####################\n")
            f.write(f"[{timestamp}] {event_type}\n")

    def on_start_click(b):
        nonlocal started
        if not started:
            log_event("Session started")
            started = True
            status_label.value = "<b style='font-size:1.5em;'>状态：</b><span style='color:green; font-size:1.5em;'>● 已开始</span>"
            start_btn.disabled = True
            end_btn.disabled = False

    def on_end_click(b):
        nonlocal ended
        if started and not ended:
            log_event("Session ended")
            ended = True
            status_label.value = "<b style='font-size:1.5em;'>状态：</b><span style='color:blue; font-size:1.5em;'>● 已结束</span>"
            end_btn.disabled = True

    start_btn.on_click(on_start_click)
    end_btn.on_click(on_end_click)
    end_btn.disabled = True

    box = widgets.HBox(
        [start_btn, end_btn, status_label],
        layout=widgets.Layout(justify_content='flex-start', gap='20px')
    )
    return box