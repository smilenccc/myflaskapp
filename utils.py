import re

def parse_quiz_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正則表達式尋找所有題目區塊
    pattern = r'\(答案([A-D])\)(\d+)\.([^\n\r]+)\n((?:\([A-D]\)[^\n\r]+\n?){4})'
    matches = re.findall(pattern, content)

    questions = []
    for correct, number, question, option_block in matches:
        options = {}
        for line in option_block.strip().split('\n'):
            opt_match = re.match(r'\(([A-D])\)\s*(.+)', line)
            if opt_match:
                letter, text = opt_match.groups()
                options[letter] = text.strip()
        if len(options) == 4:
            questions.append({
                'number': int(number),
                'question': question.strip(),
                'options': options,
                'answer': correct
            })

    return questions

def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}分{sec}秒"
