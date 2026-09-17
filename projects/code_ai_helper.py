# ============================================================
# 补全代码练习 AI 助教：交互式对话模式（统一版本）
# 用法：%run projects/code_ai_helper.py <练习名>
# 练习名：从 code_problems.md 中读取
# ============================================================

import requests
import json
import os
import sys
import markdown
import datetime
import re
from IPython.display import display
import ipywidgets as widgets

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "minimax-m3:cloud"
PROJECT_DIR = "projects"


def read_file(filename):
    try:
        with open(os.path.join(PROJECT_DIR, filename), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


# ============================================================
# 从 code_problems.md 加载练习配置
# ============================================================
def load_exercises():
    exercises = {}
    content = read_file("code_problems.md")
    if not content:
        return exercises

    sections = re.split(r'\n##\s+', content)
    for section in sections[1:]:
        lines = section.strip().split('\n')
        name = lines[0].strip()
        exercises[name] = {"name": name}
        in_task = False
        in_ref = False
        task_lines = []
        ref_lines = []

        for line in lines[1:]:
            if line.startswith("title:"):
                exercises[name]["title"] = line.replace("title:", "").strip()
                in_task = False
                in_ref = False
            elif line.startswith("aux_file:"):
                exercises[name]["aux_file"] = line.replace("aux_file:", "").strip()
                in_task = False
                in_ref = False
            elif line.startswith("ex_file:"):
                exercises[name]["ex_file"] = line.replace("ex_file:", "").strip()
                in_task = False
                in_ref = False
            elif line.startswith("compile_log:"):
                exercises[name]["compile_log"] = line.replace("compile_log:", "").strip()
                in_task = False
                in_ref = False
            elif line.startswith("run_log:"):
                exercises[name]["run_log"] = line.replace("run_log:", "").strip()
                in_task = False
                in_ref = False
            elif line.startswith("task_desc:"):
                in_task = True
                in_ref = False
                first_line = line.replace("task_desc:", "").strip()
                if first_line:
                    task_lines.append(first_line)
            elif line.startswith("reference:"):
                in_task = False
                in_ref = True
                first_line = line.replace("reference:", "").strip()
                if first_line:
                    ref_lines.append(first_line)
            elif in_task and line.strip():
                task_lines.append(line.strip())
            elif in_ref and line.strip():
                ref_lines.append(line.strip())
            else:
                if in_task and line.strip():
                    task_lines.append(line.strip())
                elif in_ref and line.strip():
                    ref_lines.append(line.strip())

        if task_lines:
            exercises[name]["task_desc"] = task_lines
        if ref_lines:
            exercises[name]["reference"] = ref_lines
    return exercises


# ============================================================
# 从 code_policies.md 加载引导策略
# ============================================================
def load_code_policies():
    content = read_file("code_policies.md")
    if not content:
        return {}

    policies = {}

    general_match = re.search(r'## 通用策略\n(.*?)(?=\n## |$)', content, re.DOTALL)
    if general_match:
        policies["general"] = general_match.group(1).strip()

    exercises = load_exercises()
    for name in exercises.keys():
        pattern = rf'## {re.escape(name)} 补充\n(.*?)(?=\n## |$)'
        match = re.search(pattern, content, re.DOTALL)
        if match and match.group(1).strip():
            policies[name] = match.group(1).strip()

    return policies


def ask_ollama_stream(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            },
            timeout=120,
            stream=True
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except:
                        pass
        else:
            yield f"❌ AI 服务请求失败 (状态码: {response.status_code})"
    except requests.exceptions.ConnectionError:
        yield "❌ 无法连接到 Ollama 服务，请确保 Ollama 正在运行。"
    except Exception as e:
        yield f"❌ 发生错误: {e}"


# 对话日志记录器
class DialogLogger:
    def __init__(self, exercise, title):
        self.exercise = exercise
        self.title = title
        self.started = False

    def log(self, log_type, content):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not self.started:
            separator = "\n#################### 事件分隔 ####################\n"
            header = f"=== [{timestamp}] {self.title}练习 学生与 AI 助教对话记录 ==="
            self.started = True
        else:
            separator = ""
            header = f"=== [{timestamp}] ==="

        log_entry = f"""
{separator}
{header}
{log_type}
{content}
"""
        try:
            with open(os.path.join(PROJECT_DIR, "cfg.log"), "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠️ 写入 cfg.log 失败: {e}")


def get_system_prompt(exercise, exercises, policies):
    ex = exercises.get(exercise)
    if not ex:
        return None

    compile_log = read_file(ex.get("compile_log", ""))
    run_log = read_file(ex.get("run_log", ""))
    aux_file = read_file(ex.get("aux_file", ""))
    ex_file = read_file(ex.get("ex_file", ""))

    if not ex_file:
        return None

    compile_log_text = compile_log if compile_log else "（无编译日志，可能尚未编译）"
    run_log_text = run_log if run_log else "（无运行日志，可能尚未运行）"
    source_code = (aux_file or "") + (ex_file or "")

    task_text = "\n".join(ex.get("task_desc", []))
    ref_text = "\n".join([f"- {item}" for item in ex.get("reference", [])])
    general_policy = policies.get("general", "")
    specific_policy = policies.get(exercise, "")

    policy_text = general_policy
    if specific_policy:
        policy_text += "\n\n【本题特殊策略】\n" + specific_policy

    lines = [
        f"你是一个专业的编译系统原理课程助教。学生正在进行上下文无关文法的学习，目前是{ex.get('title', exercise)}练习。",
        "",
        "【练习任务说明】",
        task_text,
        "",
        '源代码中标记了 "// TODO:" 的位置是需要学生补全的地方。',
        "",
        "【参考答案方向】",
        ref_text,
        "",
        "【引导策略】",
        policy_text,
        "",
        "【学生当前代码】",
        "```cpp",
        source_code,
        "```",
        "",
        "【编译日志】",
        "```",
        compile_log_text,
        "```",
        "",
        "【运行日志】",
        "```",
        run_log_text,
        "```"
    ]
    return "\n".join(lines)


md = markdown.Markdown(extensions=['fenced_code', 'tables', 'nl2br'])


def render_markdown(text):
    try:
        return md.convert(text)
    except:
        return text.replace("\n", "<br>")


class AIChat:
    def __init__(self, exercise):
        self.exercise = exercise
        self.exercises = load_exercises()
        self.policies = load_code_policies()
        title = self.exercises.get(exercise, {}).get("title", exercise)
        self.logger = DialogLogger(exercise, title)

        if exercise not in self.exercises:
            print(f"❌ 未知练习: {exercise}")
            print("支持的练习: " + ", ".join(self.exercises.keys()))
            return

        self.system_prompt = get_system_prompt(exercise, self.exercises, self.policies)
        if self.system_prompt is None:
            print(f"❌ 练习 {exercise} 数据不完整")
            return

        self.logger.log("【系统提示词】", self.system_prompt)

        self.css = widgets.HTML(value="""
        <style>
        .chat-widget-container {
            display: flex;
            flex-direction: column;
            height: 500px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #fafafa;
            padding: 8px;
            overflow: hidden;
        }
        .chat-history-area {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 8px;
            padding: 4px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
        }
        .chat-history-area .user-msg {
            margin: 8px 0;
            padding: 8px 12px;
            background-color: #e3f2fd;
            border-radius: 8px;
        }
        .chat-history-area .assistant-msg {
            margin: 8px 0;
            padding: 8px 12px;
            background-color: #f5f5f5;
            border-radius: 8px;
        }
        .chat-history-area .msg-label {
            font-weight: bold;
            font-size: 14px;
        }
        .chat-history-area .user-label { color: #1565C0; }
        .chat-history-area .assistant-label { color: #2E7D32; }
        .chat-input-area {
            flex-shrink: 0;
            display: flex;
            gap: 8px;
            padding-top: 8px;
            border-top: 1px solid #e0e0e0;
        }
        .chat-input-area .widget-text {
            flex: 1;
        }
        .chat-input-area .widget-button {
            flex-shrink: 0;
        }
        </style>
        """)

        self.chat_history = widgets.HTML(
            value="",
            layout=widgets.Layout(width='100%')
        )
        self.chat_history.add_class('chat-history-area')

        self.input_box = widgets.Text(
            placeholder='输入你的问题...（按 Enter 发送）',
            layout=widgets.Layout(width='85%')
        )
        self.send_button = widgets.Button(
            description='发送',
            button_style='primary',
            layout=widgets.Layout(width='12%')
        )

        input_row = widgets.HBox([self.input_box, self.send_button])
        input_row.add_class('chat-input-area')

        self.ui = widgets.VBox(
            [self.css, self.chat_history, input_row],
            layout=widgets.Layout(width='100%')
        )
        self.ui.add_class('chat-widget-container')

        self.send_button.on_click(self.send_message)
        self.input_box.on_submit(self.send_message)

        self.messages = []
        display(self.ui)

        initial_msg = "请分析我对练习的解答，指出问题所在并引导我修改。"
        self.messages.append(("user", initial_msg))
        self.update_chat_display()

        self._call_ai(initial_msg)

    def update_chat_display(self):
        title = self.exercises.get(self.exercise, {}).get("title", self.exercise)
        html = '<div class="chat-container">'
        html += f'<div style="margin-bottom: 12px; padding: 8px; background-color: #e8f5e9; border-radius: 8px;">'
        html += f'🤖 <b>AI 助教</b> - {title}练习 | 已加载代码上下文'
        html += '</div>'

        for role, content in self.messages:
            if role == "user":
                html += '<div class="user-msg">'
                html += '<span class="msg-label user-label">👤 你:</span>'
                html += render_markdown(content)
                html += '</div>'
            else:
                html += '<div class="assistant-msg">'
                html += '<span class="msg-label assistant-label">🤖 AI:</span>'
                html += render_markdown(content)
                html += '</div>'

        html += '</div>'
        self.chat_history.value = html

        from IPython.display import display, Javascript
        display(Javascript('''
        setTimeout(function() {
            var elements = document.querySelectorAll('.widget-html');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                if (el.querySelector('.user-msg') || el.querySelector('.assistant-msg')) {
                    el.scrollTop = el.scrollHeight;
                }
            }
        }, 100);
        '''))

    def send_message(self, sender):
        text = self.input_box.value.strip()
        if not text:
            return
        self.input_box.value = ""
        self.messages.append(("user", text))
        self.update_chat_display()
        self._call_ai(text)

    def _call_ai(self, message):
        # 记录本轮学生提问（增量）
        self.logger.log(f"【学生提问第{len(self.messages)}轮】", message)

        # 构建对话历史（只用于发送给大模型，不写入日志）
        history_text = ""
        for role, content in self.messages[:-1]:
            if role == "user":
                history_text += f"学生提问: {content}\n"
            else:
                history_text += f"AI回复: {content}\n"

        full_prompt = self.system_prompt + "\n\n【对话历史】\n" + history_text + "\n\n【学生最新提问】\n" + message + "\n\n请给出引导性的分析和提示。"

        self.messages.append(("assistant", "正在思考..."))
        self.update_chat_display()

        full_reply = ""
        for chunk in ask_ollama_stream(full_prompt):
            full_reply += chunk
            self.messages[-1] = ("assistant", full_reply + " ▌")
            self.update_chat_display()

        self.messages[-1] = ("assistant", full_reply)
        self.update_chat_display()

        self.logger.log(f"【AI回复第{len(self.messages)}轮】", full_reply)


# 解析命令行参数
exercises = load_exercises()
if len(sys.argv) < 2:
    print("❌ 请指定练习名称")
    print("支持的练习: " + ", ".join(exercises.keys()))
    print("示例: %run projects/code_ai_helper.py trans")
else:
    exercise = sys.argv[1]
    if exercise not in exercises:
        print(f"❌ 未知练习: {exercise}")
        print("支持的练习: " + ", ".join(exercises.keys()))
    else:
        ai_chat = AIChat(exercise)