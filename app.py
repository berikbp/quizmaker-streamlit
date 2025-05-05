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

    if st.button("Сохранить вопрос"):
        
        if not text:
            st.error("Введите текст вопроса.")
            return

        if qtype in ["Один ответ", "Множественный выбор"]:
            if not choices:
                st.error("Добавьте хотя бы один вариант.")
                return
            
            corr_list = correct if isinstance(correct, list) else [correct]
            if not corr_list or any(not c for c in corr_list):
                st.error("Выберите правильный(ые) ответ(ы).")
                return

            choices_str = "|".join(choices)
            correct_str = "|".join(corr_list)
        else:
            if not correct:
                st.error("Введите текстовый ответ.")
                return
            choices_str = ""
            correct_str = correct


        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO questions (text,type,choices,correct,points,tags) VALUES (?,?,?,?,?,?)",
            (text, qtype, choices_str, correct_str, points, tags)
        )
        conn.commit()
        conn.close()
        st.success("Вопрос сохранён!")

# ---------------------------------
# Page: Create a new test (wizard)
# ---------------------------------
def create_test_wizard_page():
    """Мастер создания теста в два шага"""
    st.header("🛠️ Мастер создания теста")
    st.markdown("Начните с заполнения названия, описания и тегов — затем нажмите **Далее**.")


    if "wizard" not in st.session_state:
        st.session_state.wizard = {
            "step":      1,
            "name":      "",
            "desc":      "",
            "tags":      "",
            "questions": []
        }
    w = st.session_state.wizard

    if w["step"] == 1:
        with st.form("wizard_step1"):
            name_in  = st.text_input("Название теста", value=w["name"])
            desc_in  = st.text_area("Описание теста", value=w["desc"])
            tags_in  = st.text_input("Теги теста (через запятую)", value=w["tags"])
            go       = st.form_submit_button("Далее →")

        if go:
            if not name_in.strip():
                st.error("❌ Название теста не может быть пустым!")
            else:
                
                w["name"] = name_in.strip()
                w["desc"] = desc_in
                w["tags"] = tags_in
                w["step"] = 2
        return  


    st.subheader("Шаг 2: Выберите или создайте вопросы")
    st.markdown("""
  1. Сперва вы создаете вопросы
  2. Дальше добавляете в созданнные вопросы в тест
""")

    col1, col2 = st.columns(2)

    # Left: existing questions multiselect
    with col1:
        qs = pd.read_sql("SELECT id,text FROM questions", sqlite3.connect(DB_PATH))
        picked = st.multiselect(
            "Ваши вопросы",
            options=qs["id"],
            format_func=lambda i: qs.set_index("id").at[i, "text"],
            key="wizard_picked"
        )
        w["questions"] = picked

    # Right: form to add a new question inline
    with col2:
        with st.form("wizard_new_question"):
            qtext   = st.text_input("Текст вопроса", key="new_qtext")
            qtype   = st.selectbox("Тип вопроса", ["Один ответ","Множественный выбор","Текстовый ответ"], key="new_qtype")
            qpoints = st.number_input("Баллы", min_value=1, value=1, key="new_qpoints")
            qtags   = st.text_input("Теги (через запятую)", key="new_qtags")

            if qtype in ["Один ответ","Множественный выбор"]:
                raw = st.text_area("Варианты (по строкам)", key="new_qchoices")
                choices = [c.strip() for c in raw.splitlines() if c.strip()]
                if qtype == "Один ответ":
                    correct = st.selectbox("Правильный ответ", choices, key="new_qcorrect_single")
                else:
                    correct = st.multiselect("Правильные ответы", choices, key="new_qcorrect_multi")
            else:
                correct = st.text_input("Правильный ответ", key="new_qcorrect_text")
                choices = []

            add_q   = st.form_submit_button("Добавить")
            reset_q = st.form_submit_button("Очистить")

        if add_q:
            if not qtext:
                st.error("❌ Текст вопроса обязателен")
            elif qtype != "Текстовый ответ" and not choices:
                st.error("❌ Нужно хотя бы один вариант")
            elif not correct:
                st.error("❌ Укажите правильный ответ")
            else:
                ch_str   = "|".join(choices)
                corr_str = "|".join(correct) if isinstance(correct, list) else str(correct)
                conn     = sqlite3.connect(DB_PATH)
                cur      = conn.cursor()
                cur.execute(
                    "INSERT INTO questions (text,type,choices,correct,points,tags) VALUES (?,?,?,?,?,?)",
                    (qtext, qtype, ch_str, corr_str, qpoints, qtags)
                )
                new_id = cur.lastrowid
                conn.commit()
                conn.close()

                st.success(f"✅ Вопрос ID {new_id} сохранён")
                w["questions"].append(new_id)

        if reset_q:
            for k in [
                "new_qtext","new_qtype","new_qpoints","new_qtags",
                "new_qchoices","new_qcorrect_single","new_qcorrect_multi","new_qcorrect_text"
            ]:
                st.session_state.pop(k, None)

    # Finalize test creation
    if st.button("✅ Создать тест"):
        if not w["questions"]:
            st.error("❌ Добавьте хотя бы один вопрос")
        else:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            
            cur.execute(
                "INSERT INTO tests (name,description,tags) VALUES (?,?,?)",
                (w["name"], w["desc"], w["tags"])
            )
            test_id = cur.lastrowid
            for idx, qid in enumerate(w["questions"], start=1):
                cur.execute(
                    "INSERT INTO test_questions (test_id,question_id,position) VALUES (?,?,?)",
                    (test_id, qid, idx)
                )
            conn.commit()
            conn.close()

            st.success(f"🎉 Тест ID {test_id} успешно создан!")
    
            del st.session_state.wizard


    
#List all tests
def list_tests_page():
    st.header("📚 Список тестов")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM tests", conn)
    conn.close()

    if df.empty:
        st.info("Тестов ещё нет.")
        return

    all_tags = set()
    for tag_str in df['tags'].fillna("").tolist():
        for t in tag_str.split(","):
            t = t.strip()
            if t:
                all_tags.add(t)
    all_tags = sorted(all_tags)

    #Filter 
    selected_tags = st.multiselect("Фильтровать по тегам", all_tags)
    if selected_tags:
        df = df[df['tags'].fillna("").apply(
            lambda tag_str: any(t in tag_str.split(",") for t in selected_tags)
        )]


    name_query = st.text_input("Поиск по названию")
    if name_query:
        df = df[df['name'].str.contains(name_query, case=False, na=False)]

    # Pagination
    PAGE_SIZE = 5
    total_pages = (len(df) - 1) // PAGE_SIZE + 1
    page = st.number_input("Страница", 1, total_pages, 1, 1)
    start, end = (page - 1) * PAGE_SIZE, page * PAGE_SIZE

    st.write(f"Показаны {start+1}–{min(end, len(df))} из {len(df)} тестов")
    st.dataframe(df.iloc[start:end])



def take_full_test_page():
    st.header("📝 Пройти тест (все вопросы на одной странице)")

    # Load all available tests
    conn = sqlite3.connect(DB_PATH)
    tests_df = pd.read_sql("SELECT id, name FROM tests", conn)
    conn.close()
    if tests_df.empty:
        st.info("Сначала создайте тест!")
        return


    options = [f"{r.id}: {r.name}" for r in tests_df.itertuples()]
    choice = st.selectbox("Выберите тест", options)
    test_id = int(choice.split(":", 1)[0])


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
        st.warning("В этом тесте пока нет вопросов!")
        return


    if "fulltest_submitted" not in st.session_state:
        st.session_state.fulltest_submitted = False
        st.session_state.fulltest_score = 0
        st.session_state.fulltest_max = 0


    with st.form("full_test_form"):
        answers = {}
        for q in questions:
            st.subheader(q["text"])
            opts = q["choices"].split("|") if q["type"] != "Текстовый ответ" else []
            if q["type"] == "Один ответ":
                answers[q["id"]] = st.radio("", opts, key=f"qa_{q['id']}")
            elif q["type"] == "Множественный выбор":
                answers[q["id"]] = st.multiselect("", opts, key=f"qa_{q['id']}")
            else:
                answers[q["id"]] = st.text_input("Ваш ответ", key=f"qa_{q['id']}")
        submitted = st.form_submit_button("Отправить все ответы")


    # On submit, calculate total and max score
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

        st.session_state.fulltest_submitted = True
        st.session_state.fulltest_score = total_score
        st.session_state.fulltest_max = max_score


    if st.session_state.fulltest_submitted:
        st.success(
            f"Вы набрали {st.session_state.fulltest_score} из "
            f"{st.session_state.fulltest_max} баллов."
        )

        user = st.text_input("Введите ваше имя для рейтинга",
                             key="fulltest_user")
        if st.button("Сохранить результат", key="save_fulltest_button"):
            if not user.strip():
                st.error("Введите имя, чтобы сохранить результат.")
            else:
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO scores (user, score) VALUES (?, ?)",
                    (user.strip(), st.session_state.fulltest_score)
                )
                conn.commit()
                conn.close()
                st.success("Результат сохранён!")
                
                st.session_state.fulltest_submitted = False 



#  Rating leaderboard
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


# Editing 
def edit_test_page():
    st.header("✏️ Управление тестами и вопросами")
    conn = sqlite3.connect(DB_PATH)
    tests = pd.read_sql("SELECT id, name FROM tests", conn)
    conn.close()

    if tests.empty:
        st.info("Пока нет ни одного теста.")
        return

    test_id = st.selectbox(
        "Выберите тест для редактирования",
        options=tests["id"],
        format_func=lambda i: f"{i}: {tests.loc[tests.id==i,'name'].iloc[0]}"
    )


    with st.expander("🖉 Изменить название/описание/теги"):
        row = tests.set_index("id").loc[test_id]
        new_name = st.text_input("Название теста", value=row.name)
        new_desc = st.text_area("Описание", value=row.get("description",""))
        new_tags = st.text_input("Теги", value=row.get("tags",""))
        if st.button("Сохранить метаданные", key="save_meta"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "UPDATE tests SET name=?, description=?, tags=? WHERE id=?",
                (new_name, new_desc, new_tags, test_id)
            )
            conn.commit()
            conn.close()
            st.success("Метаданные обновлены!")
    
    
    current_qs = pd.read_sql(
        "SELECT q.id, q.text FROM questions q "
        " JOIN test_questions tq ON q.id=tq.question_id "
        " WHERE tq.test_id=? ORDER BY tq.position",
        sqlite3.connect(DB_PATH), params=(test_id,)
    )
    with st.expander("🗑️ Удалить вопросы из этого теста"):
        to_remove = st.multiselect(
            "Выберите вопросы",
            options=current_qs["id"],
            format_func=lambda i: current_qs.loc[current_qs.id==i,"text"].iat[0]
        )
        if st.button("Удалить из теста", key="del_from_test"):
            conn = sqlite3.connect(DB_PATH)
            conn.executemany(
                "DELETE FROM test_questions WHERE test_id=? AND question_id=?",
                [(test_id, q) for q in to_remove]
            )
            conn.commit()
            conn.close()
            st.success(f"Удалено {len(to_remove)} вопрос(ов) из теста.")
            


    all_qs = pd.read_sql("SELECT id, text FROM questions", sqlite3.connect(DB_PATH))
    avail = all_qs[~all_qs.id.isin(current_qs.id)]
    with st.expander("➕ Добавить в тест новые вопросы"):
        to_add = st.multiselect(
            "Выберите вопросы",
            options=avail["id"],
            format_func=lambda i: avail.loc[avail.id==i,"text"].iat[0]
        )
        if st.button("Добавить в тест", key="add_to_test"):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            last_pos = cur.execute(
                "SELECT COALESCE(MAX(position),0) FROM test_questions WHERE test_id=?",
                (test_id,)
            ).fetchone()[0]
            for q in to_add:
                last_pos += 1
                cur.execute(
                    "INSERT INTO test_questions(test_id,question_id,position) VALUES(?,?,?)",
                    (test_id, q, last_pos)
                )
            conn.commit()
            conn.close()
            st.success(f"Добавлено {len(to_add)} вопрос(ов).")
            


    with st.expander("🗑️ Удалить любые вопросы из БД"):
        df_q = pd.read_sql("SELECT id, text FROM questions", sqlite3.connect(DB_PATH))
        to_del_q = st.multiselect(
            "Вопросы для удаления",
            options=df_q["id"],
            format_func=lambda i: f"{i}: {df_q.loc[df_q.id==i,'text'].iloc[0]}"
        )
        if st.button("Удалить выбранные вопросы", key="del_any_q"):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            cur.executemany(
                "DELETE FROM test_questions WHERE question_id=?",
                [(q,) for q in to_del_q]
            )
            
            cur.executemany(
                "DELETE FROM questions WHERE id=?",
                [(q,) for q in to_del_q]
            )
            conn.commit()
            conn.close()
            st.success(f"Удалено {len(to_del_q)} вопрос(ов) из БД.")
            
            
    with st.expander("🗑️ Удалить тесты из БД"):
        df_t = pd.read_sql("SELECT id, name FROM tests", sqlite3.connect(DB_PATH))
        to_del_t = st.multiselect(
            "Тесты для удаления",
            options=df_t["id"],
            format_func=lambda i: f"{i}: {df_t.loc[df_t.id==i,'name'].iloc[0]}"
        )
        if st.button("Удалить выбранные тесты", key="del_any_t"):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            for t in to_del_t:
                cur.execute("DELETE FROM test_questions WHERE test_id=?", (t,))
                cur.execute("DELETE FROM tests WHERE id=?", (t,))
            conn.commit()
            conn.close()
            st.success(f"Удалено {len(to_del_t)} тест(ов).")
            
  
def main():
    init_db()
    st.sidebar.title("QuizMaker")
    page = st.sidebar.radio("Меню", [
        "Мастер создания теста",
        "Добавить вопрос",  
        "Список тестов",
        "Редактировать тест",
        "Пройти тест",
        "Рейтинг"
    ])

    if page == "Добавить вопрос":
        add_question_page()
    elif page == "Мастер создания теста":
        create_test_wizard_page()  
    elif page == "Список тестов":
        list_tests_page()
    elif page == "Редактировать тест":
        edit_test_page() 
    elif page == "Пройти тест":
        take_full_test_page()
    elif page == "Рейтинг":
        rating_page()

if __name__ == "__main__":
    main()
