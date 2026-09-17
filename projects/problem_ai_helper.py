# ============================================================
# 思考题 AI 助教：引导学生思考 CFG 相关概念
# 用法：%run projects/problem_ai_helper.py <思考题编号>
# ============================================================

import requests
import json
import markdown
import datetime
import os
import sys
import re
from IPython.display import display, Javascript
import ipywidgets as widgets

OLLAMA_HOST = "http://localhost:11434"
# 默认使用免费的本地模型；可通过环境变量覆盖。 / Use a free local model by default; allow an environment override.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")
PROJECT_DIR = "projects"
LOG_FILE = "cfg.log"

def read_file(filename):
    try:
        with open(os.path.join(PROJECT_DIR, filename), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None

def load_problems():
    problems = {}
    content = read_file("problems.md")
    if not content:
        return problems

    sections = re.split(r'\n##\s+', content)
    for section in sections[1:]:
        lines = section.strip().split('\n')
        qid = lines[0].strip()
        problems[qid] = {"id": qid}
        in_ref = False
        in_question = False
        ref_lines = []
        question_lines = []

        for line in lines[1:]:
            if line.startswith("title:"):
                problems[qid]["title"] = line.replace("title:", "").strip()
                in_question = False
                in_ref = False
            elif line.startswith("question:"):
                in_question = True
                in_ref = False
                first_line = line.replace("question:", "").strip()
                if first_line:
                    question_lines.append(first_line)
            elif line.startswith("reference:"):
                in_question = False
                in_ref = True
                first_line = line.replace("reference:", "").strip()
                if first_line:
                    ref_lines.append(first_line)
            elif in_question and line.strip():
                question_lines.append(line.strip())
            elif in_ref and line.strip():
                ref_lines.append(line.strip())

        if question_lines:
            problems[qid]["question"] = "\n".join(question_lines)
        if ref_lines:
            problems[qid]["reference"] = ref_lines
    return problems

def load_policies():
    content = read_file("problem_policies.md")
    if not content:
        return {}
    policies = {}
    general_match = re.search(r'## 通用策略\n(.*?)(?=\n## |$)', content, re.DOTALL)
    if general_match:
        policies["general"] = general_match.group(1).strip()

    # 动态获取当前所有的题目 ID
    for qid in load_problems().keys():
        pattern = rf'## {re.escape(qid)} 补充\n(.*?)(?=\n## |$)'
        match = re.search(pattern, content, re.DOTALL)
        if match and match.group(1).strip():
            policies[qid] = match.group(1).strip()
    return policies

def ask_ollama_stream(prompt):
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "options": {"temperature": 0.4, "num_ctx": 8192},
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

class DialogLogger:
    def __init__(self, question_id):
        self.question_id = question_id
        self.started = False

    def log(self, log_type, content):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not self.started:
            separator = "\n#################### 事件分隔 ####################\n"
            header = f"=== [{timestamp}] 思考题{self.question_id} 学生与 AI 助教对话记录 ==="
            self.started = True
        else:
            separator = ""
            header = f"=== [{timestamp}] ==="
        log_entry = f"\n{separator}\n{header}\n{log_type}\n{content}\n"
        try:
            with open(os.path.join(PROJECT_DIR, LOG_FILE), "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠️ 写入 {LOG_FILE} 失败: {e}")

def get_system_prompt(question_id, problems, policies):
    q = problems.get(question_id)
    if not q:
        return None
    ref_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(q.get("reference", []))])
    general_policy = policies.get("general", "")
    specific_policy = policies.get(question_id, "")
    policy_text = general_policy
    if specific_policy:
        policy_text += "\n\n【本题特殊策略】\n" + specific_policy
    return f"""你是一个专业的编译原理课程助教，正在引导学生思考上下文无关文法相关的问题。

【问题】
{q["question"]}

【参考答案方向】
{ref_text}

【引导策略】
{policy_text}

请开始引导学生思考。"""

md = markdown.Markdown(extensions=['fenced_code', 'tables', 'nl2br'])

def render_markdown(text):
    try:
        return md.convert(text)
    except:
        return text.replace("\n", "<br>")

class ThinkingAIChat:
    def __init__(self, question_id):
        self.question_id = question_id
        self.problems = load_problems()
        self.policies = load_policies()
        self.logger = DialogLogger(question_id)

        if question_id not in self.problems:
            print(f"❌ 未知思考题编号: {question_id}")
            return

        self.system_prompt = get_system_prompt(question_id, self.problems, self.policies)
        if self.system_prompt is None:
            return

        self.logger.log("【系统提示词】", self.system_prompt)

        self.css = widgets.HTML(value="""
        <style>
        .chat-widget-container {
            display: flex; flex-direction: column; height: 500px;
            border: 1px solid #e0e0e0; border-radius: 8px;
            background-color: #fafafa; padding: 8px; overflow: hidden;
        }
        .chat-history-area {
            flex: 1; overflow-y: auto; margin-bottom: 8px; padding: 4px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6;
        }
        .chat-history-area .user-msg { margin: 8px 0; padding: 8px 12px; background-color: #e3f2fd; border-radius: 8px; }
        .chat-history-area .assistant-msg { margin: 8px 0; padding: 8px 12px; background-color: #f5f5f5; border-radius: 8px; }
        .chat-history-area .msg-label { font-weight: bold; font-size: 14px; }
        .chat-history-area .user-label { color: #1565C0; }
        .chat-history-area .assistant-label { color: #2E7D32; }
        .chat-input-area { flex-shrink: 0; display: flex; gap: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; }
        </style>
        """)

        self.chat_history = widgets.HTML(value="", layout=widgets.Layout(width='100%'))
        self.chat_history.add_class('chat-history-area')
        self.input_box = widgets.Text(placeholder='输入你的回答...（按 Enter 发送）', layout=widgets.Layout(width='85%'))
        self.send_button = widgets.Button(description='发送', button_style='primary', layout=widgets.Layout(width='12%'))

        input_row = widgets.HBox([self.input_box, self.send_button])
        input_row.add_class('chat-input-area')

        self.ui = widgets.VBox([self.css, self.chat_history, input_row], layout=widgets.Layout(width='100%'))
        self.ui.add_class('chat-widget-container')

        self.send_button.on_click(self.send_message)
        self.input_box.on_submit(self.send_message)

        self.messages = []
        display(self.ui)

        question_text = self.problems[question_id]["question"]
        initial_msg = f"请思考：{question_text}\n\n请给出你的理解和答案，我会和你一起探讨。"
        self.messages.append(("assistant", initial_msg))
        self.update_chat_display()
        self.logger.log("【助教初始提问】", initial_msg)

    def update_chat_display(self):
        title = self.problems.get(self.question_id, {}).get("title", self.question_id)
        html = f'<div style="margin-bottom:12px;padding:8px;background-color:#fff3e0;border-radius:8px;text-align:left;font-weight:bold;">💭 思考题助教 - {self.question_id} {title}</div>'
        for role, content in self.messages:
            if role == "user":
                html += f'<div class="user-msg"><span class="msg-label user-label">👤 你:</span> {render_markdown(content)}</div>'
            else:
                html += f'<div class="assistant-msg"><span class="msg-label assistant-label">🤖 助教:</span> {render_markdown(content)}</div>'
        self.chat_history.value = html
        display(Javascript('''
        setTimeout(function() {
            var elements = document.querySelectorAll('.widget-html');
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                if (el.querySelector('.user-msg') || el.querySelector('.assistant-msg')) { el.scrollTop = el.scrollHeight; }
            }
        }, 100);
        '''))

    def send_message(self, sender):
        text = self.input_box.value.strip()
        if not text: return
        self.input_box.value = ""
        self.messages.append(("user", text))
        self.update_chat_display()
        self._call_ai(text)

    def _call_ai(self, message):
        self.logger.log(f"【学生回答第{len(self.messages)}轮】", message)
        history_text = ""
        for role, content in self.messages[:-1]:
            if role == "user": history_text += f"学生回答: {content}\n"
            else: history_text += f"助教: {content}\n"
        full_prompt = self.system_prompt + f"\n\n【对话历史】\n{history_text}\n\n【学生最新回答】\n{message}\n\n请评价学生的回答，给出引导性的反馈。"

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

if len(sys.argv) < 2:
    print("❌ 请指定思考题编号")
    print("支持的编号: " + ", ".join(load_problems().keys()))
else:
    question_id = sys.argv[1]
    ai_chat = ThinkingAIChat(question_id)
