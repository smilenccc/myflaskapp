import os
import random
import time
import re
from flask import session

def parse_quiz_file(text):
    questions = []
    blocks = re.split(r'\n\s*\n', text.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if not lines or not lines[0].startswith('(答案'):
            continue

        answer_line = lines[0]
        match = re.match(r'\(答案([A-D])\)(\d+)', answer_line)
        if not match:
            continue

        answer = match.group(1)
        question_line = lines[1] if len(lines) > 1 else ''
        options = lines[2:6] if len(lines) >= 6 else []

        if len(options) == 4:
            questions.append({
                'answer': answer,
                'question': question_line.strip(),
                'options': [opt.strip() for opt in options]
            })

    return questions

def sample_questions(all_questions, q_range, q_total):
    if q_range:
        try:
            parts = q_range.replace('~', '-').split('-')
            start = int(parts[0]) - 1
            end = int(parts[1]) if len(parts) > 1 else len(all_questions)
            selected = all_questions[start:end]
        except:
            selected = all_questions
    else:
        selected = all_questions

    if q_total and q_total < len(selected):
        selected = random.sample(selected, q_total)
    return selected

def format_time(seconds):
    return time.strftime('%M:%S', time.gmtime(seconds))
