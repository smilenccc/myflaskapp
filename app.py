# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, re, random, time

app = Flask(__name__)
app.secret_key = 'temporary_testing_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USERS = {
    'smile': {'password': 'smile', 'role': 'admin'},
    'linda': {'password': '123', 'role': 'user'},
    'smile2': {'password': '123', 'role': 'user'}
}

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        if user in USERS and USERS[user]['password'] == pwd:
            session['user'] = user
            session['role'] = USERS[user]['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="帳號或密碼錯誤")
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    uploaded_files = sorted([
        f for f in os.listdir(UPLOAD_FOLDER)
        if f.endswith('.txt') and '[解析]' in f
    ])

    error = None
    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        file = request.files.get('quizfile')

        filepath = None
        if session['role'] == 'admin' and file and file.filename.endswith('.txt') and '[解析]' in file.filename:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        elif selected_file and selected_file.endswith('.txt') and '[解析]' in selected_file:
            filepath = os.path.join(UPLOAD_FOLDER, selected_file)
        else:
            error = '請上傳或選擇格式正確的 [解析] 題庫檔案（.txt）'
            return render_template('index.html', files=uploaded_files, role=session['role'], error=error)

        try:
            with open(filepath, encoding='utf-8') as f:
                questions = parse_questions(f.read())
        except Exception as e:
            return render_template('index.html', files=uploaded_files, role=session['role'], error=f'讀取題庫失敗：{e}')

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

    return render_template('index.html', files=uploaded_files, role=session['role'])

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
            'correct_text': correct_text,
            'selected_text': selected_text,
            'answer_time': answer_time
        }

        if session['mode'] == 'normal':
            if is_correct:
                session['correct'] += 1
            else:
                q['selected'] = selected_text
                q['correct_text'] = correct_text
                q['answer_time'] = answer_time
                session['wrong_list'].append(q)
        else:
            if not is_correct:
                q['selected'] = selected_text
                q['correct_text'] = correct_text
                q['answer_time'] = answer_time
                session['wrong_list'].append(q)

        session['current'] += 1
        return redirect(url_for('feedback'))

    session['question_start_time'] = time.time()
    return render_template('quiz.html', question=q, current=session['current']+1, total=len(session['questions']), time_limit=session.get('time_limit', 0))

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
        username = session.get('user', 'guest')
        filename = f'quiz_result_{username}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for q in wrong_list:
                f.write(q['full'] + '\n')
                f.write(f"[選擇] {q.get('selected', '')}\n")
                f.write(f"[正解] {q.get('correct_text', '')}\n")
                f.write(f"[時間] {q.get('answer_time', 0)} 秒\n\n")

    return render_template('result.html', correct=correct, total=total, wrong=len(wrong_list), total_time=total_time)

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
    return render_template('review_result.html', wrong=len(session.get('wrong_list', [])))

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    filename = f'quiz_result_{username}.txt'
    records = []
    if os.path.exists(filename):
        with open(filename, encoding='utf-8') as f:
            blocks = f.read().strip().split('\n\n')
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 5:
                    q_text = lines[0]
                    opts = lines[1:5]
                    selected = next((line for line in lines if line.startswith('[選擇]')), '')
                    correct = next((line for line in lines if line.startswith('[正解]')), '')
                    sec = next((line for line in lines if line.startswith('[時間]')), '')
                    records.append({
                        'question': q_text,
                        'options': opts,
                        'selected': selected.replace('[選擇]', '').strip(),
                        'correct': correct.replace('[正解]', '').strip(),
                        'seconds': sec.replace('[時間]', '').strip()
                    })
    return render_template('history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)