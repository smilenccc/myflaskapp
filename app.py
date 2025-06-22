from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, re, random, time

app = Flask(__name__)
app.secret_key = 'temporary_testing_key'

# 伺服器端 Session 設定
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = './uploads'
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
    if request.method == 'POST':
        file = request.files.get('quizfile')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            with open(filepath, encoding='utf-8') as f:
                questions = parse_questions(f.read())
        else:
            return render_template('index.html', error='未上傳題庫檔案！')

        random.shuffle(questions)
        session['questions'] = questions
        session['current'] = 0
        session['correct'] = 0
        session['wrong_list'] = []
        session['start_time'] = time.time()
        return redirect(url_for('quiz'))

    return render_template('index.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or session['current'] >= len(session['questions']):
        return redirect(url_for('result'))

    current_question = session['questions'][session['current']]

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        answer_time = round(time.time() - session.get('question_start_time', time.time()), 2)

        is_correct = selected_answer == current_question['answer']
        if is_correct:
            session['correct'] += 1
        else:
            session['wrong_list'].append(current_question)

        session['feedback'] = {
            'is_correct': is_correct,
            'correct_answer': current_question['answer'],
            'selected_answer': selected_answer,
            'answer_time': answer_time
        }

        session['current'] += 1
        return redirect(url_for('feedback'))

    session['question_start_time'] = time.time()
    return render_template('quiz.html', question=current_question, current=session['current']+1, total=len(session['questions']))

@app.route('/feedback')
def feedback():
    feedback = session.get('feedback', {})
    return render_template('feedback.html', feedback=feedback)

@app.route('/result')
def result():
    total_time = round(time.time() - session.get('start_time', time.time()), 2)
    correct = session.get('correct', 0)
    total = len(session.get('questions', []))

    # 錯誤題目寫入 quiz_result.txt
    wrong_list = session.get('wrong_list', [])
    if wrong_list:
        with open('quiz_result.txt', 'w', encoding='utf-8') as f:
            for q in wrong_list:
                f.write(q['full'] + '\n\n')

    return render_template('result.html', correct=correct, total=total, total_time=total_time, wrong=len(wrong_list))

if __name__ == '__main__':
    app.run(debug=True)
