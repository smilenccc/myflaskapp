from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session
import os, re, random, time, datetime, json

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
    """
    強化的解析邏輯 (區塊切割法)：
    1. 清除雜訊 / 正規化換行
    2. 使用 regex 定位所有題目的「開頭」：(答案)題號.題目
       - 支援括號、題號、點號之間的任意空白 (包括無空白)
    3. 兩個題目開頭之間的文字，全部歸給上一題，再從中解析選項
    """
    questions = []
    
    # === 1. 清除雜訊 / 正規化 ===
    # 移除 BOM、統一換行符號，這些都是安全的處理，不會造成 SyntaxError
    text = text.replace('\ufeff', '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. 定義題目開頭的 Regex
    # ^\s* : 行首允許空白
    # \(([A-D])\) : 抓取答案 (A)~(D)
    # \s* : 允許答案後有空白 (關鍵！解決 (B) 1. 和 (B)1. 的差異)
    # (\d+)     : 抓取題號
    # \.        : 抓取點號
    # \s* : 允許點號後有空白 (關鍵！解決 1.納 和 1. 納 的差異)
    # (.*)      : 抓取同一行剩餘的題目文字
    q_start_pattern = re.compile(r'^\s*\(([A-D])\)\s*(\d+)\.\s*(.*)', re.MULTILINE)
    
    # 找出所有題目的起始位置
    matches = list(q_start_pattern.finditer(text))
    
    for i, match in enumerate(matches):
        answer = match.group(1)       # 正解
        index = int(match.group(2))   # 題號
        title_start = match.group(3).strip()  # 題目第一行
        
        # 決定這個題目的「結束位置」 (即下一題的開始，或是檔案結尾)
        start_pos = match.start()
        if i < len(matches) - 1:
            end_pos = matches[i+1].start()
        else:
            end_pos = len(text)
            
        # 取得這一題的完整原始區塊 (包含換行、選項等)
        full_block = text[start_pos:end_pos]
        # 跳過 match 第一行，後面內容用來找選項／題目延伸
        content_block = text[match.end():end_pos]
        
        # 3. 在內容區塊中解析選項
        q_content = title_start
        options = {}
        
        # 將區塊切成行，去掉空白行
        lines = [line.strip() for line in content_block.split('\n') if line.strip()]
        
        current_part = 'QUESTION'  # 狀態標記：目前正在讀取 題目 還是 選項
        
        for line in lines:
            # 檢查這行是不是選項開頭 (A), (B), (C), (D)
            opt_match = re.match(r'^\(([A-D])\)\s*(.*)', line)
            
            if opt_match:
                # 發現新選項，切換狀態
                opt_label = opt_match.group(1)
                opt_text = opt_match.group(2).strip()
                options[opt_label] = opt_text
                current_part = opt_label  # 標記現在正在讀取哪個選項
            else:
                # 這行不是選項開頭，代表是上一部分的延續 (多行題目 或 多行選項)
                if current_part == 'QUESTION':
                    q_content += " " + line
                elif current_part in ['A', 'B', 'C', 'D']:
                    options[current_part] += " " + line

        # 檢查是否完整 (至少要有兩個選項才算一題，避免格式錯誤導致崩潰)
        if len(options) >= 2:
            questions.append({
                'index': index,
                'question': q_content,
                'options': options,
                'answer': answer,
                'full': full_block.strip()
            })
            
    return questions

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('[解析]') and f.endswith('.txt')]
    uploaded_files.sort()
    error = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload':
            if session['role'] == 'admin':
                quizfile = request.files.get('quizfile')
                if quizfile and quizfile.filename:
                    filename = quizfile.filename
                    # 簡單過濾路徑符號
                    if '/' in filename:
                        filename = filename.split('/')[-1]
                    if '\\' in filename:
                        filename = filename.split('\\')[-1]
                        
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    quizfile.save(path)
                    flash(f'題庫 "{filename}" 上傳成功！', 'success')
                    return redirect(url_for('index'))
                else:
                    flash("請選擇要上傳的檔案", 'error')
            else:
                flash("權限不足，無法上傳", 'error')

        elif action == 'start':
            selected_file = request.form.get('selected_file')
            q_range = request.form.get('q_range', '')
            q_count = request.form.get('q_count', type=int)
            time_limit = request.form.get('time_limit', type=int, default=0)

            if not selected_file:
                flash("請選擇一個題庫檔案", 'error')
            else:
                session['filename'] = selected_file
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
                
                questions = []
                try:
                    with open(full_path, encoding='utf-8') as f:
                        content = f.read()
                        questions = parse_questions(content)
                except Exception as e:
                    flash(f"讀取失敗：{e}", 'error')
                    return render_template('index.html', files=uploaded_files, error=error, role=session['role'])

                if not questions:
                    flash("題庫解析失敗或為空 (請檢查檔案內容格式)", 'error')
                else:
                    # 題號範圍篩選
                    if '-' in q_range:
                        try:
                            start, end = map(int, q_range.split('-'))
                            questions = [q for q in questions if start <= q['index'] <= end]
                        except:
                            pass
                    
                    # 題數抽樣
                    if q_count and q_count < len(questions):
                        questions = random.sample(questions, q_count)
                    
                    session['questions'] = questions
                    session['current'] = 0
                    session['start_time'] = time.time()
                    session['score'] = 0
                    session['total'] = len(questions)
                    session['wrong_list'] = []
                    session['time_limit'] = time_limit
                    session.pop('review_mode', None)
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
            'selected_letter': selected,
            'correct_letter': correct,
            'selected_text': q['options'].get(selected, ''),
            'correct_text': q['options'].get(correct, ''),
            'selected_answer': f"({selected}) {q['options'].get(selected, '')}" if selected else '',
            'correct_answer': f"({correct}) {q['options'].get(correct, '')}",
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

    # review_mode：錯題重答模式
    if session.get('review_mode'):
        wrong_list = session.get('wrong_list', [])
        if not wrong_list:
            session.pop('review_mode')
        return render_template('review_result.html', wrong=len(wrong_list))

    # 寫入個人錯題紀錄檔
    if session.get('wrong_list'):
        username = session['username']
        quiz_name = session.get('filename', '未知題庫')
        with open(f'quiz_result_{username}.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n==== 題庫：{quiz_name} ====\n")
            for q in session['wrong_list']:
                full_text = q.get('full', q.get('question', ''))
                f.write(full_text + '\n')
                f.write(f"[選擇] {q.get('selected', '')}\n")
                f.write(f"[正解] {q.get('correct_text', '')}\n")
                f.write(f"[時間] {q.get('answer_time', 0)} 秒\n\n")

    # 更新分數歷史紀錄 (JSON)
    history_path = f"scores_{session['username']}.json"
    records = []
    if os.path.exists(history_path):
        with open(history_path, encoding='utf-8') as f:
            try:
                records = json.load(f)
            except:
                records = []
    
    records.append({
        'quizfile': session.get('filename'),
        'score': score,
        'total': total,
        'accuracy': round(score / total * 100, 2),
        'time_used': time_used,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return render_template('result.html', score=score, total=total, time_used=time_used, correct=correct, incorrect=incorrect)

@app.route('/review')
def review():
    # 錯題重答
    if 'wrong_list' not in session or not session['wrong_list']:
        return redirect(url_for('index'))
    session['questions'] = session['wrong_list']
    session['current'] = 0
    session['score'] = 0
    session['total'] = len(session['questions'])
    session['wrong_list'] = []
    session['start_time'] = time.time()
    session['review_mode'] = True
    return redirect(url_for('quiz'))

@app.route('/history')
def history():
    # 歷史錯題列表
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
    records.reverse()
    return render_template('history.html', records=records)

@app.route('/score')
def score():
    if 'username' not in session:
        return redirect(url_for('login'))
    history_path = f"scores_{session['username']}.json"
    records = []
    if os.path.exists(history_path):
        with open(history_path, encoding='utf-8') as f:
            try:
                records = json.load(f)
            except:
                records = []
    records.reverse()
    return render_template('score.html', records=records, username=session['username'])

if __name__ == '__main__':
    app.run(debug=True)
