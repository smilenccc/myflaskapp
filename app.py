import os
import time
from flask import Flask, render_template, request, redirect, url_for, session
from utils import parse_quiz_file, format_time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.txt')]
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
    return redirect(url_for('index'))

@app.route('/start', methods=['POST'])
def start():
    filename = request.form.get('quiz_file')
    if not filename:
        return redirect(url_for('index'))
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    quiz = parse_quiz_file(filepath)
    session['quiz'] = quiz
    session['start_time'] = time.time()
    session['current_index'] = 0
    session['correct_count'] = 0
    session['results'] = []
    return redirect(url_for('quiz'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        selected = request.form.get('option')
        idx = session['current_index']
        quiz = session['quiz']
        correct = quiz[idx]['answer']
        correct_text = quiz[idx]['options'][correct]
        is_correct = selected == correct
        if is_correct:
            session['correct_count'] += 1
        elapsed = time.time() - session['start_time']
        session['results'].append({
            'question': quiz[idx]['question'],
            'selected': selected,
            'correct': correct,
            'correct_text': correct_text,
            'is_correct': is_correct,
            'time': format_time(elapsed)
        })
        session['start_time'] = time.time()
        return render_template('feedback.html', result=session['results'][-1], next_index=idx + 1)

    idx = session.get('current_index', 0)
    quiz = session.get('quiz', [])
    if idx >= len(quiz):
        return redirect(url_for('result'))
    question = quiz[idx]
    return render_template('quiz_step.html', index=idx+1, total=len(quiz), question=question)

@app.route('/next')
def next():
    session['current_index'] += 1
    return redirect(url_for('quiz'))

@app.route('/result')
def result():
    return render_template('result.html', results=session.get('results', []), score=session.get('correct_count', 0))
