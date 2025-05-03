import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "data/questions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            type TEXT,
            choices TEXT,
            correct TEXT,
            points INTEGER,
            tags TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_question_page():
    st.header("➕ Добавить новый вопрос")
    text = st.text_input("Текст вопроса")
    qtype = st.selectbox("Тип вопроса", ["Один ответ", "Множественный выбор", "Текстовый ответ"])
    points = st.number_input("Баллы за вопрос", min_value=1, value=1)
    tags = st.text_input("Теги (через запятую)")

    if qtype in ["Один ответ", "Множественный выбор"]:
        raw = st.text_area("Варианты ответов (каждый с новой строки)")
        choices = [c.strip() for c in raw.splitlines() if c.strip()]
        if qtype == "Один ответ":
            correct = st.selectbox("Правильный ответ", choices)
        else:
            correct = st.multiselect("Правильные ответы", choices)
    else:
        correct = st.text_input("Правильный текстовый ответ")

    if st.button("Сохранить"):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO questions (text,type,choices,correct,points,tags) VALUES (?,?,?,?,?,?)",
            (text, qtype, "|".join(choices) if qtype!="Текстовый ответ" else "",
             str(correct), points, tags)
        )
        conn.commit()
        conn.close()
        st.success("Вопрос сохранён!")

def list_tests_page():
    st.header("📋 Список вопросов")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM questions", conn)
    conn.close()
    st.dataframe(df[["id","text","type","points","tags"]])

def take_test_page():
    st.header("📝 Пройти тест")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, text FROM questions", conn)
    conn.close()
    qid = st.selectbox("Выберите вопрос по ID", df["id"])
    if st.button("Загрузить вопрос"):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT text,type,choices,correct,points FROM questions WHERE id=?", (qid,)).fetchone()
        conn.close()
        if row:
            text, qtype, raw, correct, points = row
            st.subheader(text)
            if qtype == "Один ответ":
                ans = st.radio("", raw.split("|"))
            elif qtype == "Множественный выбор":
                ans = st.multiselect("", raw.split("|"))
            else:
                ans = st.text_input("Ваш ответ")
            if st.button("Проверить"):
                ok = (ans == correct) or (set(ans) == set(eval(correct)))
                st.write("✅ Правильно!" if ok else "❌ Неправильно!")
        else:
            st.error("Вопрос не найден.")

def main():
    init_db()
    st.sidebar.title("QuizMaker")
    page = st.sidebar.radio("Навигация", ["Добавить вопрос", "Список тестов", "Пройти тест"])
    if page == "Добавить вопрос":
        add_question_page()
    elif page == "Список тестов":
        list_tests_page()
    else:
        take_test_page()

if __name__ == "__main__":
    main()
