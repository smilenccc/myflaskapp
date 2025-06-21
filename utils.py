import re
import random

def parse_questions(text):
    blocks = text.strip().split("\n\n")
    questions = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 6:
            continue

        answer_line = lines[0].strip()
        match = re.match(r"\(答案\)([A-D])", answer_line)
        if not match:
            continue
        answer = match.group(1)

        question_line = lines[1].strip()
        question_match = re.match(r"(\d+)[\.\、．](.*)", question_line)
        if question_match:
            question_text = question_match.group(2).strip()
        else:
            question_text = question_line

        options = lines[2:6]
        if not all(opt.startswith(("(A)", "(B)", "(C)", "(D)")) for opt in options):
            continue

        questions.append({
            "question": question_text,
            "options": options,
            "answer": answer
        })

    return questions
