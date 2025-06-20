import re
import random

def parse_questions(text):
    pattern = r"\([A-D]\)\d+\..*?(?=(\n\([A-D]\)\d+\.|\Z))"
    matches = re.finditer(pattern, text, re.DOTALL)
    questions = []
    for match in matches:
        full_match = match.group(0).strip()
        lines = full_match.split("\n")
        first_line = lines[0]
        options = lines[1:]
        correct_match = re.match(r"\(([A-D])\)(\d+\..+)", first_line)
        if not correct_match:
            continue
        correct_option = correct_match.group(1)
        question_text = correct_match.group(2)
        questions.append({
            "question": question_text.strip(),
            "options": options,
            "answer": correct_option,
            "full": full_match
        })
    return questions

def filter_question_range(questions, range_str):
    if not range_str:
        return questions
    match = re.match(r"(\d+)\s*[-~]\s*(\d+)", range_str)
    if not match:
        return questions
    start, end = int(match.group(1)), int(match.group(2))
    filtered = []
    for q in questions:
        match_num = re.match(r"(\d+)\.", q["question"])
        if match_num:
            q_num = int(match_num.group(1))
            if start <= q_num <= end:
                filtered.append(q)
    return filtered

def sample_questions(questions, target_count=50):
    if not questions:
        return []
    total = len(questions)
    group_size = total // target_count
    remainder = total % target_count
    sampled = []
    i = 0
    for _ in range(target_count - 1):
        block = questions[i:i + group_size]
        if block:
            sampled.append(random.choice(block))
        i += group_size
    block = questions[i:]
    if block:
        sampled.append(random.choice(block))
    return sampled
