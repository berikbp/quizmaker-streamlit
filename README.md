# QuizMaker
### Интерактивное веб-приложение для создания, редактирования и прохождения тестов

## Описание

QuizMaker — это сайт созданный на Streamlit, которое позволяет:

- Делать вопросы трёх видов: один ответ, несколько ответов или просто написать текст. Можно проставить баллы и теги.

- Собирать эти вопросы в тест через двухшаговый мастер (сначала вводишь название/описание, потом выбираешь вопросы).

- Ре-редактировать и удалять тесты и вопросы в одном месте, не надо прыгать по вкладкам.

- Фильтровать тесты по тегу и искать по названию (ну типа “математика”, “шашки”).

- Проходить тесты и сразу видеть свой результат.

- Сохранять имена и баллы юзеров, смотреть лидерборд.

- БД простая — SQLite, а для табличек используется Pandas.

##  Установка и запуск
 1. **Clone the repo**  
   ```bash
   git clone https://github.com/berikbp/quizmaker-streamlit.git
   cd quizmaker-streamlit
```
 2. Создайте и активируйте виртуальное окружение

Сперва пишите 
```bash
python -m venv .venv

```
Дальше 
   Linux/macOS:
source .venv/bin/activate
```bash
   source .venv/bin/activate
```

Windows (cmd.exe): 
cmd

```bash
   .\.venv\Scripts\activate.bat
```
Windows (PowerShell):

powershell:
```bash
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

может быть такое что потребует .venv\Scripts\Activate.ps1
```

 4. Установите зависимости
```bash
pip install -r requirements.txt
```
когда скачиваете зависимости убедитесь что requirements.txt не должен расположен ни в каких папках, если оно в папке вытащите его

 5. Запустите приложение
```bash
streamlit run app.py
```
## Описание процесса проектирования и разработки. 
1. Сбор и анализ требований

        Выявлены ключевые сценарии: создание вопросов, группировка их в тесты, фильтрация/поиск тестов, прохождение тестов и сохранение результатов.

        Определены роли: администратор (создаёт и редактирует тесты), пользователь (проходит тест и смотрит рейтинг).

2. Проектирование архитектуры

        Лёгковесная СУБД SQLite для хранения вопросов, тестов, связей и результатов — всё в одном файле, без серверных зависимостей.

        Чёткое разделение на страницы/функции: CRUD вопросов, мастер создания теста, список и поиск тестов, прохождение теста, рейтинг, единственная «редактирование» вкладка для всех операций.

3. Разработка MVP в итерациях

        Итерация 1: базовый CRUD — добавление, просмотр и удаление вопросов и тестов.

        Итерация 2: мастер создания теста в два шага с session_state для сохранения промежуточных данных.

        Итерация 3: фильтры по тегам, поиск по названию, пагинация, рейтинг пользователей.

        Итерация 4: объединение функций удаления/редактирования в один универсальный UI (edit_test_page с экспандерами).

4. Тестирование:

        Ручное прохождение всех сценариев: добавление/редактирование/удаление вопросов и тестов, проверка порядка вопросов, сохранение и отображение рейтинга.

        Исправление багов с потерей session_state, отложенная инициализация ключей и валидация пустых полей.

## Уникальные подходы и методологии
- Wizard-паттерн для многoшагового создания теста: сначала метаданные, потом выбор/создание вопросов, при этом все данные живут в одном объекте в st.session_state.

- Использование Streamlit Forms для локальной валидации и предотвращения перезагрузки страницы при каждом вводе.

- Все в одном: SQLite + Pandas + Streamlit, без лишних заморочек

- UI через st.expander: компактная панель для группировки похожих операций в редакторе теста (metadata, add/remove вопросы, удаление тестов).

## Обсуждение компромиссов и как я их решил
1. База данных: Postgres vs SQLite
    Я сначала хотел использовать Postgres — думал, что это «правильно». Но настроить его на хостинге и потыкаться с подключением заняло слишком много времени. Вместо этого я взял SQLite и написал функцию init_db(), которая сама создаёт все таблицы при старте. Так проще запускать у себя локально и не париться с миграциями — в продакшене, конечно, Postgres лучше, но для MVP SQLite сойдет.

2. Хранение вариантов и правильных ответов
    Сначала я хотел сделать отдельную таблицу для каждого варианта ответа и связывать её с вопросом через JOIN. Но это усложнило код и замедляло разработку. Я придумал проще: склеивать все варианты в одну строку через | и обратно разделять в коде (split("|")). Да, это костыль и в будущем может вызвать проблемы с расширением схемы, но пока работает быстро и без лишних таблиц.

3. Удобство редактирования vs чистота кода
    В начале я сделал отдельные страницы «Удалить вопросы» и «Удалить тесты», но пользователям приходилось шариться по меню. Я собрал всё в одну вкладку Редактировать тест с раскрывающимися секциями (expander). Код стал заметно больше, но зато интерфейс стал понятнее: выбрал тест — и сразу можешь менять его метаданные, добавлять или удалять вопросы.
Каждое из таких решений помогло сэкономить время и упростить разработку, пусть и ценой некоторого «грязного» кода. Если проект будет расти — я точно переработаю БД, варианты ответов и добавлю нормальную аутентификацию

## Известные баги и косяки
- Иногда кнопки надо жать дважды, пока форма “подхватит” данные.

- Текстовый ответ проверяется очень строго — без учёта регистра и пробелов.

- Нет возможности экспортировать/импортировать тесты, только ручками через БД.

- В будущем будуи проблемы с масштабированием, нету принципов ООП и все записано на один файл(извините я не думал что все распишу на один файл, пока я этого осознал,уже было поздно)

- Недавно только понял, если перезагрузить ноут, облако не сохранит созданные тесты, так как файловая система сама по себе не постоянна, нужно интегрировать внешние БД 


## Объясните почему выбрали этот технический стэк
Почему я выбрал такой стек технологий
1. Python + Streamlit

    Потому что это очень просто и быстро: пару строчек кода — и готов веб-интерфейс.

    Не надо возиться с фронтендом на JavaScript, всё сразу видно в браузере.

2. SQLite

    Это такая легкая база, хранящаяся в одном файле.

    Не нужно настраивать сложные сервера баз данных — всё работает «из коробки».

3. Pandas

    С ним удобно забрасывать данные из базы в таблички и сразу показывать их в приложении.

    Легко фильтровать, сортировать и собирать статистику.

3. Streamlit Forms и session_state

    Формы (st.form) помогают собирать данные и обрабатывать их только после клика по кнопке.

    st.session_state сохраняет промежуточные ответы и выборы без танцев с JavaScript.


В итоге получилось лёгкое, но надёжное веб-приложение для создания и прохождения тестов, которое можно запустить где угодно за пару минут. Я выбрал этот стек, потому что он прост в освоении и позволяет элегантно реализовать всю логику без лишнего «костыльного» кода. Если бы я делал всё на чистом HTML/CSS/JavaScript, мне бы не удалось так быстро и плавно воплотить весь текущий функционал.


## Планы на будущее (бонусные уровни)

Изначально я хотел реализовать все бонусные уровни, в том числе:
- Авторизацию и регистрацию пользователей  
- Персональную статистику прогресса и достижения  
- Режим соревнования в реальном времени  
- Генерацию тестов через LLM API  

Но времени было слишком мало — за 4 дня я не успел покрыть всё это, и решил сфокусироваться на основной, ключевой функциональности.  
Если появится возможность продолжить развитие проекта, первым делом добавлю аутентификацию и личный кабинет.


## В целом про свой опыт опыт разработки:
Мне в целом не нравится заниматься фронтендом, но с помощью вашей программы я многому научился:

Связыванию базы данных с библиотеками Python,

Простым способам фронтенд-разработки,

И в целом приобрёл очень ценный опыт.

Эти четыре дня дались мне тяжело, ведь я студент, у меня тоже есть дедлайны, мидтермы и незаконченные дела в университете.
Да, сайт не удивляет: он написан в одном файле, без OOP-принципов, но я всё равно постарался и справился со стрессом и этим испытанием.

Хочется поблагодарить вас за возможность учиться и становиться сильнее.

С благодарностью,
Сатыбалды Берик






Я второй раз отправил свою форму, потому что заметил что мой деплой не сохранял его в Absolute Path,  понял это и решил отредактировать и решить 
в целом так я еще сделал записал видео про мою мотивацию, еще раз спасибо
