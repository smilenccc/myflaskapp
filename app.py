from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os, re, random, time

app = Flask(__name__)
app.secret_key = 'temporary_testing_key'

# Session 設定
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
    uploaded_files = sorted([
        f for f in os.listdir(UPLOAD_FOLDER)
        if f.endswith('.txt') and '[解析]' in f
    ])

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        file = request.files.get('quizfile')

        filepath = None

        # 優先使用上傳的檔案
        if file and file.filename.endswith('.txt') and '[解析]' in file.filename:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        elif selected_file and selected_file.endswith('.txt') and '[解析]' in selected_file:
            filepath = os.path.join(UPLOAD_FOLDER, selected_file)
        else:
            return render_template('index.html', files=uploaded_files, error='請上傳或選擇格式正確的 [解析] 題庫檔案（.txt）')

        # 題庫解析
        try:
            with open(filepath, encoding='utf-8') as f:
                questions = parse_questions(f.read())
        except Exception as e:
            return render_template('index.html', files=uploaded_files, error=f'讀取題庫失敗：{e}')

        # 出題範圍、數量、時限處理
        q_range = request.form.get('q_range', '').strip()
        q_count = int(request.form.get('q_count', 50))
        time_limit = int(request.form.get('time_limit', 0))

        if q_range:
            match = re.match(r'(\\d+)\\s*[-~]\\s*(\\d+)', q_range)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                questions = [
                    q for q in questions
                    if start <= int(re.match(r'(\\d+)\\.', q['question']).group(1)) <= end
                ]

        random.shuffle(questions)
        questions = questions[:q_count]

        # 建立 session 狀態
        session['questions'] = questions
        session['current'] = 0
        session['correct'] = 0
        session['wrong_list'] = []
        session['start_time'] = time.time()
        session['time_limit'] = time_limit

        return redirect(url_for('quiz'))

    return render_template('index.html', files=uploaded_files)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or session['current'] >= len(session['questions']):
        return redirect(url_for('result'))

    q = session['questions'][session['current']]

    if request.method == 'POST':
        selected = request.form.get('answer')
        answer_time = round(time.time() - session.get('question_start_time', time.time()), 2)
        is_correct = selected == q['answer']
        if is_correct:
            session['correct'] += 1
        else:
            session['wrong_list'].append(q)

        session['feedback'] = {
            'is_correct': is_correct,
            'correct_answer': q['answer'],
            'selected_answer': selected,
            'answer_time': answer_time
        }

        session['current'] += 1
        return redirect(url_for('feedback'))

    session['question_start_time'] = time.time()
    return render_template('quiz.html',
                           question=q,
                           current=session['current']+1,
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

if __name__ == '__main__':
    app.run(debug=True)
