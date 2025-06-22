from flask import Flask, render_template, request, redirect, url_for, session
import os
import re
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 從test50.py複製而來的parse_questions函數
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
    if request.method == 'POST':
        file = request.files['quizfile']
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            with open(filepath, encoding='utf-8') as f:
                session['questions'] = parse_questions(f.read())
                random.shuffle(session['questions'])
            session['current'] = 0
            session['correct'] = 0
            return redirect(url_for('quiz'))
    return render_template('index.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or session['current'] >= len(session['questions']):
        return redirect(url_for('result'))

    q = session['questions'][session['current']]

    if request.method == 'POST':
        answer = request.form.get('answer')
        if answer == q['answer']:
            session['correct'] += 1
        session['current'] += 1
        return redirect(url_for('quiz'))

    return render_template('quiz.html', question=q, current=session['current']+1, total=len(session['questions']))

@app.route('/result')
def result():
    correct = session.get('correct', 0)
    total = len(session.get('questions', []))
    return render_template('result.html', correct=correct, total=total)

if __name__ == '__main__':
    app.run(debug=True)
