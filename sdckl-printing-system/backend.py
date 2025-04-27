from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = 'sdckl-printing-system.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open('sdckl-printing-system/schema.sql') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO students (student_id, name) VALUES (?, ?)', (student_id, name))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Student ID already registered.", 400
        conn.close()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/wallet/<student_id>', methods=['GET'])
def wallet(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404
    balance = 0.0
    transactions = conn.execute('SELECT * FROM wallet_transactions WHERE student_id = ? ORDER BY timestamp DESC', (student['id'],)).fetchall()
    for t in transactions:
        if t['transaction_type'] == 'credit':
            balance += t['amount']
        else:
            balance -= t['amount']
    conn.close()
    return render_template('wallet.html', student=student, balance=balance, transactions=transactions)

@app.route('/wallet/<student_id>/add', methods=['POST'])
def add_funds(student_id):
    amount = float(request.form['amount'])
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404
    conn.execute('INSERT INTO wallet_transactions (student_id, amount, transaction_type) VALUES (?, ?, ?)', (student['id'], amount, 'credit'))
    conn.commit()
    conn.close()
    return redirect(url_for('wallet', student_id=student_id))

@app.route('/print/<student_id>', methods=['GET', 'POST'])
def print_job(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if student is None:
        conn.close()
        return "Student not found", 404
    if request.method == 'POST':
        pages = int(request.form['pages'])
        cost_per_page = 0.10
        cost = pages * cost_per_page
        # Calculate current balance
        transactions = conn.execute('SELECT * FROM wallet_transactions WHERE student_id = ? ORDER BY timestamp DESC', (student['id'],)).fetchall()
        balance = 0.0
        for t in transactions:
            if t['transaction_type'] == 'credit':
                balance += t['amount']
            else:
                balance -= t['amount']
        if balance < cost:
            conn.close()
            return "Insufficient funds", 400
        # Deduct cost and record print job
        conn.execute('INSERT INTO wallet_transactions (student_id, amount, transaction_type) VALUES (?, ?, ?)', (student['id'], cost, 'debit'))
        conn.execute('INSERT INTO print_jobs (student_id, pages, cost) VALUES (?, ?, ?)', (student['id'], pages, cost))
        conn.commit()
        conn.close()
        return redirect(url_for('wallet', student_id=student_id))
    conn.close()
    return render_template('print.html', student=student)

if __name__ == '__main__':
    import os
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
