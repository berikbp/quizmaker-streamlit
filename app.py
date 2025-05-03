import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = "data/questions.db"

# Initialize database and tables
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores(
            user TEXT,
            score INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
            (text, qtype, "|".join(choices) if qtype!="Текстовый ответ" else "", str(correct), points, tags)
        )
        conn.commit()
        conn.close()
        st.success("Вопрос сохранён!")

def list_tests_page():
    st.header("📋 Список вопросов")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM questions", conn)
    conn.close()

    all_tags = sorted({tag for tags in df["tags"] for tag in tags.split(",") if tag})
    selected_tags = st.multiselect("Фильтровать по тегам", all_tags)
    text_query = st.text_input("Поиск по тексту")

    if selected_tags:
        df = df[df["tags"].apply(lambda s: any(t in s.split(",") for t in selected_tags))]
    if text_query:
        df = df[df["text"].str.contains(text_query, case=False, na=False)]

    PAGE_SIZE = 5
    total_pages = max((len(df) - 1) // PAGE_SIZE + 1, 1)
    page_num = st.number_input("Страница", min_value=1, max_value=total_pages, value=1, step=1)
    start = (page_num - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    st.write(f"Показаны записи с {start+1} по {min(end, len(df))} из {len(df)}")
    st.dataframe(df.iloc[start:end][["id","text","type","points","tags"]])

def rating_page():
    st.header("🏆 Рейтинг пользователей")
    conn = sqlite3.connect(DB_PATH)
    df_scores = pd.read_sql(
        "SELECT user, SUM(score) AS total_score FROM scores GROUP BY user ORDER BY total_score DESC",
        conn
    )
    conn.close()

    if df_scores.empty:
        st.info("Пока нет сохранённых результатов.")
    else:
        st.table(df_scores)

def take_test_page():
    st.header("📝 Пройти тест")
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
        st.session_state.current_type = None
        st.session_state.current_raw = None
        st.session_state.current_correct = None
        st.session_state.current_points = 0
        st.session_state.pending_score = None  # Track pending score

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT id, text FROM questions", conn)
    conn.close()
    qid = st.selectbox("Выберите вопрос по ID", df["id"])

    if st.button("Загрузить вопрос"):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT text,type,choices,correct,points FROM questions WHERE id=?", (qid,)
        ).fetchone()
        conn.close()
        if row:
            text, qtype, raw, correct, points = row
            st.session_state.current_question = text
            st.session_state.current_type = qtype
            st.session_state.current_raw = raw
            st.session_state.current_correct = correct
            st.session_state.current_points = points

    if st.session_state.current_question:
        st.subheader(st.session_state.current_question)
        with st.form("answer_form"):
            if st.session_state.current_type == "Один ответ":
                ans = st.radio("", st.session_state.current_raw.split("|"))
            elif st.session_state.current_type == "Множественный выбор":
                ans = st.multiselect("", st.session_state.current_raw.split("|"))
            else:
                ans = st.text_input("Ваш ответ")
            submitted = st.form_submit_button("Проверить")

        if submitted:
            correct = st.session_state.current_correct
            correct_list = []
            if isinstance(ans, list):
                try:
                    correct_list = eval(correct)
                except Exception:
                    correct_list = []
            is_ok = set(ans) == set(correct_list) if isinstance(ans, list) else (ans == correct)

            if is_ok:
                st.success("✅ Правильно!")
                score = st.session_state.current_points
            else:
                st.error("❌ Неправильно!")
                score = 0
            st.session_state.pending_score = score  # Store score to session state

    # Display save form if there's a pending score
    if st.session_state.get("pending_score") is not None:
        with st.form("save_score_form"):
            user = st.text_input("Введите ваше имя для рейтинга", key="save_username")
            save_clicked = st.form_submit_button("Сохранить результат")
        if save_clicked and user:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO scores (user, score) VALUES (?, ?)",
                         (user, st.session_state.pending_score))
            conn.commit()
            conn.close()
            st.success("Результат сохранён!")
            del st.session_state.pending_score  # Clear pending score

def main():
    init_db()
    st.sidebar.title("QuizMaker")
    page = st.sidebar.radio("Навигация", [
        "Добавить вопрос",
        "Список вопросов",
        "Пройти тест",
        "Рейтинг"
    ])
    if page == "Добавить вопрос":
        add_question_page()
    elif page == "Список вопросов":
        list_tests_page()
    elif page == "Пройти тест":
        take_test_page()
    else:
        rating_page()

if __name__ == "__main__":
    main()