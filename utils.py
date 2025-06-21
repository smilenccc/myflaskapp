import re

def parse_quiz_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 將每一題以「(答案A)1.」類型斷開
    pattern = r"\(答案([A-D])\)(\d+)\.([^\n]*)\n((?:\([A-D]\)[^\n]+\n?){4})"
    matches = re.findall(pattern, content)

    questions = []
    for answer, number, question_text, options_text in matches:
        options = {}
        for opt_line in options_text.strip().split('\n'):
            opt_match = re.match(r"\(([A-D])\)\s*(.*)", opt_line)
            if opt_match:
                opt_key, opt_val = opt_match.groups()
                options[opt_key] = opt_val
        if len(options) == 4:
            questions.append({
                'number': int(number),
                'question': question_text.strip(),
                'options': options,
                'answer': answer
            })

    return questions

def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}分 {sec}秒"
