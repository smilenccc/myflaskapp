import re

def parse_quiz_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r"\(答案([A-D])\)(\d+)[^\n]*?\n(.*?)\n\(A\)(.*?)\n\(B\)(.*?)\n\(C\)(.*?)\n\(D\)(.*?)(?:\n|$)"
    matches = re.findall(pattern, content, re.DOTALL)

    questions = []
    for ans, qid, question, a, b, c, d in matches:
        questions.append({
            "id": int(qid),
            "question": question.strip(),
            "options": {
                "A": a.strip(),
                "B": b.strip(),
                "C": c.strip(),
                "D": d.strip(),
            },
            "answer": ans
        })
    return questions

def format_time(seconds):
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins} 分 {secs} 秒"
