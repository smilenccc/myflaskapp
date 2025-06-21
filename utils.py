import re

def parse_quiz_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    pattern = r'\(答案([A-D])\)(\d+)\.?(.+?)\n\((A\).+?)\n\((B\).+?)\n\((C\).+?)\n\((D\).+?)\n'
    matches = re.findall(pattern, text, re.DOTALL)

    quiz = []
    for ans, number, question, a, b, c, d in matches:
        quiz.append({
            'id': int(number),
            'question': question.strip(),
            'options': {
                'A': a[2:].strip(),
                'B': b[2:].strip(),
                'C': c[2:].strip(),
                'D': d[2:].strip()
            },
            'answer': ans
        })

    return quiz

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"
