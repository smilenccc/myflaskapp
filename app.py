# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, re, random, time

app = Flask(__name__)
app.secret_key = 'temporary_testing_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = './uploads'
HISTORY_FILE = './history.txt'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
        if correct_match:
            correct_option = correct_match.group(1)
            question_text = correct_match.group(2)
            questions.append({
                "question": question_text.strip(),
                "options": options,
                "answer": correct_option,
                "full": full_match
            })
    return questions


@app.route('/', methods=['GET', 'POST'])
def index():
    uploaded_files = sorted([
        f for f in os.listdir(UPLOAD_FOLDER)
        if f.endswith('.txt') and '[解析]' in f
    ])

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        file = request.files.get('quizfile')

        filepath = None
        if file and file.filename.endswith('.txt') and '[解析]' in file.filename:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        elif selected_file and selected_file.endswith('.txt') and '[解析]' in selected_file:
            filepath = os.path.join(UPLOAD_FOLDER, selected_file)
        else:
            return render_template('index.html', files=uploaded_files, error='請上傳或選擇格式正確的 [解析] 題庫檔案（.txt）')

        try:
            with open(filepath, encoding='utf-8') as f:
                questions = parse_questions(f.read())
        except Exception as e:
            return render_template('index.html', files=uploaded_files, error=f'讀取題庫失敗：{e}')

        q_range = request.form.get('q_range', '').strip()
        q_count = int(request.form.get('q_count', 50))
        time_limit = int(request.form.get('time_limit', 0))

        if q_range:
            match = re.match(r'(\d+)\s*[-~]\s*(\d+)', q_range)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                questions = [
                    q for q in questions
                    if start <= int(re.match(r'(\d+)\.', q['question']).group(1)) <= end
                ]

        random.shuffle(questions)
        questions = questions[:q_count]

        session['questions'] = questions
        session['current'] = 0
        session['correct'] = 0
        session['wrong_list'] = []
        session['start_time'] = time.time()
        session['time_limit'] = time_limit
        session['mode'] = 'normal'

        return redirect(url_for('quiz'))

    return render_template('index.html', files=uploaded_files)


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or session['current'] >= len(session['questions']):
        return redirect(url_for('result' if session['mode'] == 'normal' else 'review_result'))

    q = session['questions'][session['current']]

    if request.method == 'POST':
        selected = request.form.get('answer')
        answer_time = round(time.time() - session.get('question_start_time', time.time()), 2)
        is_correct = selected == q['answer']

        selected_text = next((opt for opt in q['options'] if opt.startswith(f"({selected})")), "未選擇")
        correct_text = next((opt for opt in q['options'] if opt.startswith(f"({q['answer']})")), "未知")

        session['feedback'] = {
            'is_correct': is_correct,
            'correct_answer': correct_text,
            'selected_answer': selected_text,
            'selected_text': selected_text,
            'correct_text': correct_text,
            'answer_time': answer_time
        }

        if session['mode'] == 'normal':
            if is_correct:
                session['correct'] += 1
            else:
                session['wrong_list'].append(q)
                with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"[錯誤題目]\n{q['question']}\n你的答案: {selected_text}\n正確答案: {correct_text}\n作答時間: {answer_time} 秒\n---\n")
        else:
            if not is_correct:
                session['wrong_list'].append(q)

        session['current'] += 1
        return redirect(url_for('feedback'))

    session['question_start_time'] = time.time()
    return render_template('quiz.html',
                           question=q,
                           current=session['current'] + 1,
                           total=len(session['questions']),
                           time_limit=session.get('time_limit', 0))


@app.route('/feedback')
def feedback():
    return render_template('feedback.html', feedback=session.get('feedback', {}))


@app.route('/result')
def result():
    total_time = round(time.time() - session.get('start_time', time.time()), 2)
    correct = session.get('correct', 0)
    total = len(session.get('questions', []))
    wrong_list = session.get('wrong_list', [])

    if wrong_list:
        with open('quiz_result.txt', 'w', encoding='utf-8') as f:
            for q in wrong_list:
                f.write(q['full'] + '\n\n')

    return render_template('result.html',
                           correct=correct,
                           total=total,
                           wrong=len(wrong_list),
                           total_time=total_time)


@app.route('/review')
def review():
    wrong_list = session.get('wrong_list', [])
    if not wrong_list:
        return redirect(url_for('result'))

    session['questions'] = wrong_list
    session['current'] = 0
    session['wrong_list'] = []
    session['mode'] = 'review'
    session['start_time'] = time.time()
    return redirect(url_for('quiz'))


@app.route('/review_result')
def review_result():
    wrong_list = session.get('wrong_list', [])
    return render_template('review_result.html', wrong=len(wrong_list))


@app.route('/history')
def history():
    if not os.path.exists(HISTORY_FILE):
        return render_template('history.html', records=[])

    with open(HISTORY_FILE, encoding='utf-8') as f:
        blocks = f.read().strip().split('---\n')
        records = [block.strip() for block in blocks if block.strip()]
    return render_template('history.html', records=records)


if __name__ == '__main__':
    app.run(debug=True)
