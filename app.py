from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import time
from utils import parse_questions, filter_question_range, sample_questions

app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    quiz_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".txt")]
    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                message = "✅ 上傳成功：" + filename
        elif "quiz_file" in request.form:
            session["quiz_file"] = request.form["quiz_file"]
            session["range"] = request.form.get("range")
            session["count"] = int(request.form.get("count", 50))
            return redirect(url_for("quiz"))
    return render_template("index.html", quiz_files=quiz_files, message=message)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "quiz_file" not in session:
        return redirect(url_for("index"))

    if "questions" not in session:
        # 初次載入
        file_path = os.path.join(UPLOAD_FOLDER, session["quiz_file"])
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        all_questions = parse_questions(content)
        filtered = filter_question_range(all_questions, session.get("range"))
        selected = sample_questions(filtered, session.get("count", 50))
        session["questions"] = selected
        session["answers"] = []
        session["wrong_list"] = []
        session["current_index"] = 0
        session["start_time"] = time.time()

    index = session["current_index"]
    questions = session["questions"]
    total = len(questions)

    if request.method == "POST":
        user_ans = request.form.get("answer")
        correct_ans = questions[index]["answer"]
        if user_ans == correct_ans:
            session["answers"].append(True)
        else:
            session["answers"].append(False)
            session["wrong_list"].append(questions[index])

        session["current_index"] += 1
        if session["current_index"] >= total:
            return redirect(url_for("result"))

        return redirect(url_for("quiz"))

    # 顯示當前題目
    return render_template("quiz_step.html", q=questions[index], index=index + 1, total=total)


@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
