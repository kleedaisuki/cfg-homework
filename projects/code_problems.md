# 代码补全练习集

## 2.4
title: 最左推导与语法树生成（含优先级与括号）
aux_file: 
ex_file: student_derivation_2.4.txt
compile_log: 
run_log: 
task_desc:
  学生被要求写出句子 7-3*(4+6) 的最左推导过程。
  文法为：expr -> expr + term | expr - term | term ; term -> term * factor | term / factor | factor ; factor -> digit | ( expr ) ; digit -> 0..9
  输入规范：在 derivation_steps 列表中输入字符串，每一行包含 "=>"，=> 之后是这一步推导出的完整符号串。
reference:
  - 必须是严格的最左推导，每次替换当前串中最左侧的非终结符。
  - 核心难点在于体现优先级和括号的层次，必须逐层展开（expr -> term -> factor）。
  - 最终生成的串必须完全等于 "7-3*(4+6)" (有无空格间隔相邻终结符均可，中间推导步骤也是如此)。

## 2.5
title: 后缀表达式文法的推导与语法树
aux_file: 
ex_file: student_derivation_2.5.txt
compile_log: 
run_log: 
task_desc:
  学生被要求写出句子 aa+a* 的最左推导过程。
  文法为：S -> S S + | S S * | a
  输入规范：在 derivation_steps 列表中输入字符串，每一行包含 "=>"，=> 之后是这一步推导出的完整符号串。
reference:
  - 第一步推导必须是 S => S S *，因为最后一步运算是乘法。
  - 必须是严格的最左推导，每次替换当前串中最左侧的 S。
  - 最终生成的串必须完全等于 "aa+a*" (有无空格间隔相邻终结符均可，中间推导步骤也是如此)。