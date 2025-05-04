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

    # Questions table
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

    # Scores table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user TEXT,
            score INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tests table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            tags TEXT
        )
    """)

    # Link table between tests and questions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_questions (
            test_id INTEGER,
            question_id INTEGER,
            position INTEGER,
            PRIMARY KEY (test_id, question_id),
            FOREIGN KEY(test_id) REFERENCES tests(id),
            FOREIGN KEY(question_id) REFERENCES questions(id)
        )
    """)

    conn.commit()
    conn.close()

# Page: Add a single question
def add_question_page():
    st.header("➕ Добавить новый вопрос")
    text = st.text_input("Текст вопроса")
    qtype = st.selectbox("Тип вопроса", ["Один ответ", "Множественный выбор", "Текстовый ответ"])
    points = st.number_input("Баллы за вопрос", min_value=1, value=1)
    tags = st.text_input("Теги (через запятую)")

    # Показываем варианты только для choice-вопросов
    if qtype in ["Один ответ", "Множественный выбор"]:
        raw = st.text_area("Варианты ответов (каждый с новой строки)")
        choices = [c.strip() for c in raw.splitlines() if c.strip()]
        if qtype == "Один ответ":
            correct = st.selectbox("Правильный ответ", choices)
        else:
            correct = st.multiselect("Правильные ответы", choices)
    else:
        correct = st.text_input("Правильный текстовый ответ")

    # Сохраняем только после проверки всех полей
    if st.button("Сохранить вопрос"):
        # --- 1) Валидация ---
        if not text:
            st.error("Введите текст вопроса.")
            return

        if qtype in ["Один ответ", "Множественный выбор"]:
            if not choices:
                st.error("Добавьте хотя бы один вариант ответа.")
                return
            # correct может быть None или пустым списком
            correct_list = correct if isinstance(correct, list) else [correct]
            if not correct_list or any(ans is None or ans == "" for ans in correct_list):
                st.error("Выберите правильный(ые) ответ(ы).")
                return

            # собираем строки для БД
            choices_str = "|".join(choices)
            correct_str = "|".join(str(ans) for ans in correct_list)

        else:
            if not correct:
                st.error("Введите текстовый ответ.")
                return
            choices_str = ""
            correct_str = correct

        # --- 2) Записываем в БД ---
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO questions (text, type, choices, correct, points, tags) VALUES (?,?,?,?,?,?)",
            (text, qtype, choices_str, correct_str, points, tags)
        )
        conn.commit()
        conn.close()
        st.success("Вопрос сохранён!")

# Page: Create a new test
def create_test_page():
    st.header("🆕 Создать новый тест")
    with st.form("create_test_form"):
        name = st.text_input("Название теста")
        description = st.text_area("Описание теста")
        tags = st.text_input("Теги (через запятую)")
        if st.form_submit_button("Создать тест"):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO tests (name, description, tags) VALUES (?,?,?)",
                (name, description, tags)
            )
            test_id = cur.lastrowid
            conn.commit()
            conn.close()
            st.success(f"Тест '{name}' создан! (ID: {test_id})")

# Page: Add questions to an existing test
def add_questions_to_test_page():
    st.header("➕ Добавить вопросы в тест")
    conn = sqlite3.connect(DB_PATH)
    tests_df = pd.read_sql("SELECT id, name FROM tests", conn)
    questions_df = pd.read_sql("SELECT id, text FROM questions", conn)
    conn.close()

    if tests_df.empty:
        st.warning("Сначала создайте тест!")
        return
    if questions_df.empty:
        st.warning("Сначала добавьте вопросы!")
        return

    test_id = st.selectbox(
        "Выберите тест", tests_df['id'],
        format_func=lambda x: tests_df.loc[tests_df.id==x, 'name'].values[0]
    )
    selected = st.multiselect(
        "Выберите вопросы", questions_df['id'],
        format_func=lambda x: questions_df.loc[questions_df.id==x, 'text'].values[0]
    )

    if st.button("Добавить в тест"):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        max_pos = cur.execute(
            "SELECT MAX(position) FROM test_questions WHERE test_id=?", (test_id,)
        ).fetchone()[0] or 0
        for qid in selected:
            max_pos += 1
            cur.execute(
                "INSERT OR IGNORE INTO test_questions (test_id, question_id, position) VALUES (?,?,?)",
                (test_id, qid, max_pos)
            )
        conn.commit()
        conn.close()
        st.success(f"Добавлено {len(selected)} вопросов в тест ID {test_id}!")

# Helper: Show one question during a full test
def show_question(q_id):
    state = st.session_state
    conn = sqlite3.connect(DB_PATH)
    text, qtype, raw, correct, points = conn.execute(
        "SELECT text,type,choices,correct,points FROM questions WHERE id=?", (q_id,)
    ).fetchone()
    conn.close()

    st.subheader(text)
    if qtype == "Один ответ":
        ans = st.radio("Варианты ответа", raw.split("|"), key=f"q{q_id}")
    elif qtype == "Множественный выбор":
        ans = st.multiselect("Варианты ответа", raw.split("|"), key=f"q{q_id}")
    else:
        ans = st.text_input("Ваш ответ", key=f"q{q_id}")

    if st.button("Дальше", key=f"next{q_id}"):
        # проверка
        if isinstance(ans, list):
            is_ok = set(ans) == set(correct.split("|"))
        else:
            is_ok = (ans == correct)
        if is_ok:
            state.test_score += points
        state.current_q_index += 1
        st.experimental_rerun()

# Page: List all tests
def list_tests_page():
    st.header("📚 Список тестов")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM tests", conn)
    conn.close()
    if df.empty:
        st.info("Тестов ещё нет.")
    else:
        st.dataframe(df)

# Page: Take a full multi-question test
def take_full_test_page():
    st.header("📝 Пройти тест (все вопросы на одной странице)")

    # 1) Выбор теста
    conn = sqlite3.connect(DB_PATH)
    tests_df = pd.read_sql("SELECT id, name FROM tests", conn)
    conn.close()
    if tests_df.empty:
        st.info("Сначала создайте тест!")
        return

    test_id = st.selectbox(
        "Выберите тест",
        tests_df["id"],
        format_func=lambda x: tests_df.loc[tests_df.id == x, "name"].values[0]
    )

    # 2) Загрузка вопросов
    conn = sqlite3.connect(DB_PATH)
    questions = pd.read_sql(
        """
        SELECT q.id, q.text, q.type, q.choices, q.correct, q.points
        FROM questions q
        JOIN test_questions tq ON q.id = tq.question_id
        WHERE tq.test_id = ?
        ORDER BY tq.position
        """,
        conn,
        params=(test_id,)
    ).to_dict("records")
    conn.close()
    if not questions:
        st.warning("В этом тесте нет вопросов!")
        return

    # 3) Форма с вопросами
    answers = {}
    with st.form("full_test_form"):
        for q in questions:
            st.subheader(q["text"])
            if q["type"] == "Один ответ":
                opts = q["choices"].split("|")
                answers[q["id"]] = st.radio("", opts, key=f"qa_{q['id']}")
            elif q["type"] == "Множественный выбор":
                opts = q["choices"].split("|")
                answers[q["id"]] = st.multiselect("", opts, key=f"qa_{q['id']}")
            else:
                answers[q["id"]] = st.text_input("Ваш ответ", key=f"qa_{q['id']}")
        submitted = st.form_submit_button("Отправить все ответы")

    # 4) Подсчёт очков и сохранение в session_state
    if submitted:
        total_score = 0
        max_score = 0
        for q in questions:
            max_score += q["points"]
            user_ans = answers[q["id"]]
            correct_list = (
                q["correct"].split("|")
                if q["type"] != "Текстовый ответ"
                else [q["correct"]]
            )
            if isinstance(user_ans, list):
                if set(user_ans) == set(correct_list):
                    total_score += q["points"]
            else:
                if user_ans == correct_list[0]:
                    total_score += q["points"]

        # сохраняем результат в session_state
        st.session_state["last_score"] = total_score
        st.session_state["last_max"] = max_score

    # 5) Форма сохранения результата — показываем только после подсчёта
    if "last_score" in st.session_state:
        st.success(f"Вы набрали {st.session_state['last_score']} из {st.session_state['last_max']} баллов.")
        with st.form("save_score_form"):
            user = st.text_input("Введите ваше имя для рейтинга", key="full_test_user")
            save_clicked = st.form_submit_button("Сохранить результат")
        if save_clicked:
            if not user:
                st.error("Введите имя перед сохранением.")
            else:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO scores (user, score) VALUES (?, ?)",
                    (user, st.session_state["last_score"])
                )
                conn.commit()
                conn.close()
                st.success("Результат сохранён!")
                # убираем, чтобы форма больше не показывалась
                del st.session_state["last_score"]
                del st.session_state["last_max"]






# Page: Rating leaderboard
def rating_page():
    st.header("🏆 Рейтинг пользователей")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT user, SUM(score) AS total_score FROM scores GROUP BY user ORDER BY total_score DESC", conn
    )
    conn.close()
    if df.empty:
        st.info("Результатов ещё нет.")
    else:
        st.table(df)

# Main: navigation menu
def main():
    init_db()
    st.sidebar.title("QuizMaker")
    page = st.sidebar.radio("Меню", [
        "Добавить вопрос",
        "Создать тест",
        "Добавить вопросы в тест",
        "Список тестов",
        "Пройти тест",
        "Рейтинг"
    ])
    if page == "Добавить вопрос":
        add_question_page()
    elif page == "Создать тест":
        create_test_page()
    elif page == "Добавить вопросы в тест":
        add_questions_to_test_page()
    elif page == "Список тестов":
        list_tests_page()
    elif page == "Пройти тест":
        take_full_test_page()
    elif page == "Рейтинг":
        rating_page()

if __name__ == "__main__":
    main()
