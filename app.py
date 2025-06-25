from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, re, random, time, datetime, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = './uploads'
Session(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

USERS = {
    'smile': {'password': 'smile', 'role': 'admin'},
    'linda': {'password': '123', 'role': 'user'},
    'smile2': {'password': '123', 'role': 'user'}
}

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username]['password'] == password:
            session['username'] = username
            session['role'] = USERS[username]['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='帳號或密碼錯誤')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def parse_questions(text):
    pattern = r"\([A-D]\)\d+\..*?(?=(\n\([A-D]\)\d+\.|\Z))"
    matches = re.finditer(pattern, text, re.DOTALL)
    questions = []
    for match in matches:
        block = match.group(0).strip()
        lines = block.split('\n')
        first_line = lines[0]
        options = lines[1:]
        correct_match = re.match(r"\(([A-D])\)(\d+)\.(.*)", first_line)
        if not correct_match or len(options) != 4:
            continue
        answer = correct_match.group(1)
        index = int(correct_match.group(2))
        qtext = correct_match.group(3).strip()
        qdata = {
            'index': index,
            'question': qtext,
            'options': {opt[1]: opt[3:].strip() for opt in options if re.match(r"\([A-D]\)", opt)},
            'answer': answer,
            'full': block
        }
        questions.append(qdata)
    return questions

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('[解析]') and f.endswith('.txt')]
    error = None

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        quizfile = request.files.get('quizfile')
        q_range = request.form.get('q_range', '')
        q_count = request.form.get('q_count', type=int)
        time_limit = request.form.get('time_limit', type=int, default=0)

        if session['role'] == 'admin' and quizfile and quizfile.filename:
            filename = secure_filename(quizfile.filename)
            quizfile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            selected_file = filename

        if not selected_file:
            error = "請選擇或上傳一個題庫檔案"
        else:
            session['filename'] = selected_file
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            try:
                with open(full_path, encoding='utf-8') as f:
                    questions = parse_questions(f.read())
            except Exception as e:
                return render_template('index.html', files=uploaded_files, error=f"無法讀取題庫：{e}", role=session['role'])

            if not questions:
                error = "題庫解析失敗或為空"
            else:
                if '-' in q_range:
                    try:
                        start, end = map(int, q_range.split('-'))
                        questions = [q for q in questions if start <= q['index'] <= end]
                    except:
                        pass
                if q_count and q_count < len(questions):
                    questions = random.sample(questions, q_count)
                session['questions'] = questions
                session['current'] = 0
                session['start_time'] = time.time()
                session['score'] = 0
                session['total'] = len(questions)
                session['wrong_list'] = []
                return redirect(url_for('quiz'))

    return render_template('index.html', files=uploaded_files, error=error, role=session['role'])

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or session['current'] >= len(session['questions']):
        return redirect(url_for('result'))

    if request.method == 'POST':
        selected = request.form.get('option')
        q = session['questions'][session['current']]
        correct = q['answer']
        feedback = {
            'is_correct': selected == correct,
            'selected_answer': f"({selected}) {q['options'].get(selected, '')}",
            'correct_answer': f"({correct}) {q['options'].get(correct, '')}",
            'selected_text': q['options'].get(selected, ''),
            'correct_text': q['options'].get(correct, ''),
            'answer_time': round(time.time() - session.get('question_start', time.time()), 2)
        }
        if selected == correct:
            session['score'] += 1
        else:
            q['selected'] = feedback['selected_answer']
            q['correct_text'] = feedback['correct_answer']
            q['answer_time'] = feedback['answer_time']
            session['wrong_list'].append(q)
        session['current'] += 1
        session['last_feedback'] = feedback
        return redirect(url_for('feedback'))

    session['question_start'] = time.time()
    q = session['questions'][session['current']]
    return render_template('quiz.html', q=q, qid=session['current']+1, total=session['total'])

@app.route('/feedback')
def feedback():
    return render_template('feedback.html', feedback=session.get('last_feedback'))

@app.route('/result')
def result():
    score = session.get('score', 0)
    total = session.get('total', 1)
    time_used = round(time.time() - session.get('start_time', time.time()), 2)
    correct = score
    incorrect = total - score

    if session.get('wrong_list'):
        username = session['username']
        with open(f'quiz_result_{username}.txt', 'w', encoding='utf-8') as f:
            for q in session['wrong_list']:
                f.write(q['full'] + '\n')
                f.write(f"[選擇] {q.get('selected', '')}\n")
                f.write(f"[正解] {q.get('correct_text', '')}\n")
                f.write(f"[時間] {q.get('answer_time', 0)} 秒\n\n")

    history_path = f"scores_{session['username']}.json"
    records = []
    if os.path.exists(history_path):
        with open(history_path, encoding='utf-8') as f:
            records = json.load(f)
    records.append({
        'quizfile': session.get('filename'),
        'score': score,
        'total': total,
        'accuracy': round(score/total*100, 2),
        'time_used': time_used,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return render_template('result.html', score=score, total=total, time_used=time_used, correct=correct, incorrect=incorrect)

@app.route('/review')
def review():
    if 'wrong_list' not in session or not session['wrong_list']:
        return redirect(url_for('index'))
    session['questions'] = session['wrong_list']
    session['current'] = 0
    session['score'] = 0
    session['total'] = len(session['questions'])
    session['wrong_list'] = []
    session['start_time'] = time.time()
    return redirect(url_for('quiz'))

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))

    filename = f'quiz_result_{session["username"]}.txt'
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

@app.route('/score')
def score():
    if 'username' not in session:
        return redirect(url_for('login'))
    history_path = f"scores_{session['username']}.json"
    records = []
    if os.path.exists(history_path):
        with open(history_path, encoding='utf-8') as f:
            records = json.load(f)
    return render_template('score.html', records=records, username=session['username'])

if __name__ == '__main__':
    app.run(debug=True)
