from flask import Flask, render_template, request, redirect, url_for, session
import os
import time
from utils import parse_quiz_file, format_time

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 自動讀取 uploads/ 下的第一個題庫作為預設
quiz_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".txt")]
if quiz_files:
    default_file = os.path.join(UPLOAD_FOLDER, quiz_files[0])
    quiz_data = parse_quiz_file(default_file)
    current_filename = quiz_files[0]
else:
    quiz_data = []
    current_filename = None

@app.route('/')
def index():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".txt")]
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.txt'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
    return redirect(url_for('index'))

@app.route('/quiz', methods=['GET'])
def quiz():
    global quiz_data, current_filename
    file = request.args.get('file')
    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file)
        quiz_data = parse_quiz_file(filepath)
        current_filename = file

    if not quiz_data:
        return "目前沒有題庫，請先上傳。"

    session['current_question'] = 0
    session['start_time'] = time.time()
    session['correct_count'] = 0
    return redirect(url_for('question'))

@app.route('/question', methods=['GET', 'POST'])
def question():
    if 'current_question' not in session:
        return redirect(url_for('quiz'))

    index = session['current_question']
    if index >= len(quiz_data):
        return redirect(url_for('result'))

    question = quiz_data[index]

    if request.method == 'POST':
        selected = request.form.get('answer')
        correct = question['answer']
        elapsed_time = time.time() - session['start_time']
        session['last_time'] = format_time(elapsed_time)
        session['start_time'] = time.time()

        is_correct = selected == correct
        if is_correct:
            session['correct_count'] += 1

        session['last_result'] = {
            'selected': selected,
            'correct': correct,
            'is_correct': is_correct
        }

        session['current_question'] += 1
        return redirect(url_for('question'))

    result = session.pop('last_result', None)
    last_time = session.pop('last_time', None)
    return render_template('quiz_step.html',
                           question=question,
                           index=index + 1,
                           total=len(quiz_data),
                           result=result,
                           time_used=last_time)

@app.route('/result')
def result():
    correct = session.get('correct_count', 0)
    total = len(quiz_data)
    return render_template('result.html', correct=correct, total=total)

if __name__ == '__main__':
    app.run(debug=True)
