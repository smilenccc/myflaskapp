def parse_quiz_file(filepath):
    questions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"\((A|B|C|D)\)(\d+)\.\s*(.+)", line)
        if match:
            answer = match.group(1)
            number = match.group(2)
            question_text = match.group(3)
            options = []
            for j in range(1, 5):
                if i + j < len(lines) and re.match(r"\([A-D]\)", lines[i + j]):
                    options.append(lines[i + j])
            if len(options) == 4:
                questions.append({
                    'number': number,
                    'question': question_text,
                    'options': options,
                    'answer': answer
                })
            i += 5
        else:
            i += 1
    return questions

def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{m} 分 {s} 秒"
