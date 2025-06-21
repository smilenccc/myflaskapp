from flask import Flask, render_template, request, redirect, url_for, session
import os
import time
from utils import parse_questions

app = Flask(__name__)
app.secret_key = "your_secret_key"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("quizfile")
        if uploaded_file and uploaded_file.filename.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
            questions = parse_questions(text)
            if not questions:
                return "解析失敗，請確認題庫格式", 400
            session["questions"] = questions
            session["current_index"] = 0
            session["correct_count"] = 0
            session["start_time"] = time.time()
            session["wrong_list"] = []
            session["question_start"] = time.time()
            return redirect(url_for("quiz"))
        return "請上傳 .txt 題庫檔案"
    return render_template("index.html")

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "questions" not in session:
        return redirect(url_for("index"))

    questions = session["questions"]
    feedback = None
    time_used = None

    if request.method == "POST":
        selected = request.form.get("answer")
        q_index = session["current_index"]
        q = questions[q_index]
        correct = q["answer"]
        if selected == correct:
            session["correct_count"] += 1
            feedback = "正確！"
        else:
            feedback = f"錯誤，正確答案是 {correct}：{q['options']['ABCD'.index(correct)][3:].strip()}"
            session["wrong_list"].append(q)
        time_used = round(time.time() - session["question_start"], 2)
        session["current_index"] += 1

    if session["current_index"] >= len(questions):
        return redirect(url_for("result"))

    current_index = session["current_index"]
    q = questions[current_index if feedback is None else current_index - 1]
    if feedback is None:
        session["question_start"] = time.time()

    return render_template("quiz_step.html",
                           q=q,
                           index=(current_index if feedback is None else current_index),
                           total=len(questions),
                           feedback=feedback,
                           time_used=time_used)

@app.route("/result")
def result():
    correct = session.get("correct_count", 0)
    total = len(session.get("questions", []))
    duration = round(time.time() - session.get("start_time", time.time()), 2)
    return render_template("result.html",
                           correct=correct,
                           total=total,
                           duration=duration,
                           wrong_list=session.get("wrong_list", []))

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))
