from flask import Flask, render_template, request, redirect, session, url_for
import os
import random
import time
from utils import parse_quiz_file, format_time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_quiz_files():
    return [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.txt')]

@app.route('/')
def index():
    quiz_files = get_quiz_files()
    settings = {
        "range": "",
        "count": "",
        "time_limit": ""
    }
    return render_template('index.html', quiz_files=quiz_files, settings=settings)

@app.route('/start', methods=['POST'])
def start_quiz():
    quiz_file = request.form['quiz_file']
    range_setting = request.form.get('range', '')
    count_setting = request.form.get('count', '')
    time_limit = request.form.get('time_limit', '')

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], quiz_file)
    questions = parse_quiz_file(filepath)

    # 範圍設定
    if range_setting:
        try:
            start, end = map(int, range_setting.split('-'))
            questions = questions[start - 1:end]
        except:
            pass

    # 題數限制
    if count_setting:
        try:
            count = int(count_setting)
            questions = random.sample(questions, min(count, len(questions)))
        except:
            pass
    else:
        random.shuffle(questions)

    session['questions'] = questions
    session['current'] = 0
    session['correct'] = 0
    session['start_time'] = time.time()
    session['per_question_start'] = time.time()
    session['results'] = []

    return redirect(url_for('question'))

@app.route('/question', methods=['GET', 'POST'])
def question():
    if request.method == 'POST':
        selected = request.form.get('answer')
        current = session.get('current', 0)
        questions = session['questions']
        correct_answer = questions[current]['answer']
        elapsed = int(time.time() - session.get('per_question_start', time.time()))

        is_correct = (selected == correct_answer)
        if is_correct:
            session['correct'] += 1

        session['results'].append({
            'index': current + 1,
            'selected': selected,
            'correct': correct_answer,
            'is_correct': is_correct,
            'time': elapsed
        })

        session['current'] += 1

        if session['current'] >= len(questions):
            return redirect(url_for('result'))

        return render_template('feedback.html',
                               is_correct=is_correct,
                               correct_answer=correct_answer,
                               time=elapsed)

    current = session.get('current', 0)
    questions = session.get('questions', [])
    if current >= len(questions):
        return redirect(url_for('result'))

    session['per_question_start'] = time.time()
    q = questions[current]
    return render_template('quiz_step.html', question=q, index=current + 1, total=len(questions))

@app.route('/result')
def result():
    total_time = int(time.time() - session.get('start_time', time.time()))
    correct = session.get('correct', 0)
    total = len(session.get('questions', []))
    return render_template('result.html', correct=correct, total=total, total_time=total_time)

if __name__ == '__main__':
    app.run(debug=True)
