import os
import random
import time
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from utils import parse_quiz_file, sample_questions, format_time

app = Flask(__name__)
app.secret_key = 'quiz_secret_key'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    quiz_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.txt')]

    if request.method == 'POST':
        uploaded_file = request.files.get('quizfile')
        if uploaded_file and uploaded_file.filename.endswith('.txt'):
            path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(path)
            selected_file = uploaded_file.filename
        else:
            selected_file = request.form.get('selected_file')

        q_range = request.form.get('range', '').strip()
        q_total = request.form.get('total', '').strip()
        q_limit = request.form.get('limit', '').strip()

        session['selected_file'] = selected_file
        session['q_range'] = q_range
        session['q_total'] = int(q_total) if q_total else None
        session['q_limit'] = int(q_limit) if q_limit else None

        return redirect(url_for('start_quiz'))

    return render_template('index.html', quiz_files=quiz_files)

@app.route('/start')
def start_quiz():
    selected_file = session.get('selected_file')
    q_range = session.get('q_range')
    q_total = session.get('q_total')
    q_limit = session.get('q_limit')

    if not selected_file:
        return redirect(url_for('index'))

    path = os.path.join(UPLOAD_FOLDER, selected_file)
    with open(path, encoding='utf-8') as f:
        raw_text = f.read()

    all_questions = parse_quiz_file(raw_text)
    questions = sample_questions(all_questions, q_range, q_total)

    session['questions'] = questions
    session['current'] = 0
    session['score'] = 0
    session['start_time'] = time.time()
    session['wrong'] = []

    return redirect(url_for('quiz'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    questions = session.get('questions', [])
    current = session.get('current', 0)
    q_limit = session.get('q_limit')

    if current >= len(questions):
        return redirect(url_for('result'))

    if request.method == 'POST':
        selected = request.form.get('answer')
        elapsed = float(request.form.get('elapsed', 0))

        correct = questions[current]['answer']
        if selected == correct:
            session['score'] += 1
            correct_flag = True
        else:
            correct_flag = False
            session['wrong'].append(questions[current])

        session['current'] += 1

        return render_template('feedback.html',
                               correct=correct_flag,
                               correct_answer=correct,
                               explanation=questions[current - 1]['question'],
                               time_used=format_time(elapsed),
                               next_url=url_for('quiz'))

    question = questions[current]
    return render_template('quiz_step.html',
                           index=current + 1,
                           total=len(questions),
                           question=question,
                           time_limit=q_limit)

@app.route('/result')
def result():
    total = len(session.get('questions', []))
    score = session.get('score', 0)
    duration = time.time() - session.get('start_time', time.time())
    wrong = session.get('wrong', [])

    # 記錄錯誤題目
    if wrong:
        with open('quiz_result.txt', 'w', encoding='utf-8') as f:
            for q in wrong:
                f.write(q['question'] + '\n')
                for opt in q['options']:
                    f.write(opt + '\n')
                f.write('\n')

    return render_template('result.html',
                           score=score,
                           total=total,
                           duration=format_time(duration))

if __name__ == '__main__':
    app.run(debug=True)
