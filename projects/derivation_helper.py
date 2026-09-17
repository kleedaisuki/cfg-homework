# projects/derivation_helper.py
import os
import re
import datetime

class TreeNode:
    def __init__(self, label):
        self.label = label
        self.children = []

def tokenize(s):
    # 符号正规化：自动在括号等符号两侧补空格
    s = re.sub(r'([(){}\[\],;])', r' \1 ', s)
    return s.split()

def validate_and_draw(derivation_steps, non_terminals, target_sentence, root_label, log_filename, log_append_text=""):
    os.makedirs("projects", exist_ok=True)
    
    # 准备日志内容列表，用于收集所有输出
    log_lines = []
    def log_print(*args):
        line = " ".join(str(arg) for arg in args)
        print(line)
        log_lines.append(line)

    # 1. 保存输入供 AI 助教读取
    cfg_text = "\n".join(derivation_steps)
    with open(os.path.join("projects", log_filename), "w", encoding="utf-8") as f:
        f.write(cfg_text)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 初始日志记录
    log_lines.append("\n#################### 事件分隔 ####################")
    log_lines.append(f"=== [{timestamp}] {log_append_text} ===")
    log_lines.append(cfg_text)
    log_lines.append("") # 空行

    log_print("✅ 你的推导步骤已保存。开始验证...\n")

    # 2. 验证与绘图逻辑
    root = TreeNode(root_label)
    frontier = [root]
    valid = True

    for step in derivation_steps:
        if "=>" not in step:
            log_print(f"❌ 格式错误: '{step}'。每一行必须包含 '=>'。")
            valid = False
            break
            
        next_str = step.split("=>", 1)[1].strip()
        next_tokens = tokenize(next_str)
        curr_tokens = [n.label for n in frontier]
        
        L_idx = -1
        for i, token in enumerate(curr_tokens):
            if token in non_terminals:
                L_idx = i
                break
                
        if L_idx == -1:
            log_print(f"❌ 错误: 当前串中已没有非终结符，但仍未推导出目标句子。")
            log_print(f"   当前串: {' '.join(curr_tokens)}")
            valid = False
            break
            
        expected_prefix = curr_tokens[:L_idx]
        expected_suffix = curr_tokens[L_idx+1:]
        
        if next_tokens[:L_idx] != expected_prefix:
            log_print(f"❌ 错误: 不是最左推导或替换错误。你不应修改最左非终结符之前的部分。")
            log_print(f"   当前串: {' '.join(curr_tokens)}")
            log_print(f"   你的步骤: {' '.join(next_tokens)}")
            valid = False
            break
            
        if len(expected_suffix) > 0:
            if next_tokens[-len(expected_suffix):] != expected_suffix:
                log_print(f"❌ 错误: 不是最左推导或替换错误。你不应修改最左非终结符之后的部分。")
                log_print(f"   当前串: {' '.join(curr_tokens)}")
                log_print(f"   你的步骤: {' '.join(next_tokens)}")
                valid = False
                break
            new_rhs = next_tokens[L_idx:-len(expected_suffix)]
        else:
            new_rhs = next_tokens[L_idx:]
            
        if not new_rhs:
            log_print(f"❌ 错误: 替换后的内容为空。")
            valid = False
            break

        target_node = frontier[L_idx]
        new_nodes = [TreeNode(t) for t in new_rhs]
        target_node.children = new_nodes
        frontier = frontier[:L_idx] + new_nodes + frontier[L_idx+1:]

    if valid:
        final_str = "".join([n.label for n in frontier])
        if final_str == target_sentence:
            log_print("✅ 推导正确！最终生成句子: " + final_str)
            log_print("📊 正在生成语法树...\n")
            
            def print_tree(node, prefix="", is_last=True, is_root=True):
                if is_root:
                    log_print(node.label)
                else:
                    log_print(f"{prefix}{'└── ' if is_last else '├── '}{node.label}")
                
                if not node.children:
                    return
                    
                for i, child in enumerate(node.children):
                    child_is_last = (i == len(node.children) - 1)
                    child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")
                    print_tree(child, child_prefix, child_is_last, False)
            
            print_tree(root)
        else:
            log_print(f"❌ 推导完成但结果不匹配。当前结果: '{final_str}', 目标: '{target_sentence}'")
            log_print(f"   当前串: {' '.join([n.label for n in frontier])}")

    # 将所有收集到的输出一次性追加到统一日志
    with open(os.path.join("projects", "cfg.log"), "a", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n\n")