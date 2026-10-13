# Фудграм — подробное описание проекта

Документ описывает, что находится в каждой папке и файле проекта, как загрузить демонстрационные данные и как перенести и запустить проект на другом компьютере.

- Репозиторий: https://github.com/Flexecstasy/Foodgram
- Образы на Docker Hub: `svetlanaputana/foodgram_backend`, `svetlanaputana/foodgram_frontend`

---

## 1. Что это за проект

«Фудграм» — сайт, на котором пользователи публикуют рецепты, добавляют чужие в избранное, подписываются на авторов и формируют список покупок (одинаковые ингредиенты из разных рецептов суммируются, список скачивается файлом `.txt`).

Проект состоит из двух частей:

| Часть | Что это | Кто написал |
|---|---|---|
| **Фронтенд** | одностраничное приложение (SPA) на React | дано заранее, не изменялось |
| **Бэкенд** | REST API на Django + Django REST Framework | разработано в рамках проекта |

Работает всё в четырёх Docker-контейнерах: `nginx` (входная точка и раздача файлов), `db` (PostgreSQL), `backend` (Django + Gunicorn) и `frontend` (одноразовый контейнер, который только собирает статические файлы React и завершается).

### Как проходит запрос

```
Браузер ──► nginx :80
              ├─ /              → собранный React (файлы из frontend/build)
              ├─ /api/...       → backend (Gunicorn :8000) → Django → PostgreSQL
              ├─ /api/docs/     → статическая страница ReDoc (папка docs/)
              ├─ /admin/        → backend (админка Django)
              ├─ /s/<код>/      → backend (короткая ссылка → страница рецепта)
              ├─ /media/        → загруженные картинки (volume media)
              └─ /backend_static/ → статика админки Django (volume static)
```

---

## 2. Структура проекта

```
foodgram-student-project--main/
├── .github/workflows/main.yml
├── .gitattributes
├── .gitignore
├── README.md
├── PROJECT_GUIDE.md        ← этот файл
├── setup.cfg
├── backend/
├── frontend/
├── infra/
├── data/
├── docs/
├── postman_collection/
└── task/
```

### 2.1. Корень проекта

| Файл | Назначение |
|---|---|
| `README.md` | Краткая инструкция: стек, запуск в Docker, локальная разработка, CI/CD. |
| `PROJECT_GUIDE.md` | Этот подробный справочник. |
| `setup.cfg` | Настройки `flake8` — проверки кода на соответствие PEP 8. Исключает миграции, фронтенд, данные и т. п., для `settings.py` разрешает длинные строки. |
| `.gitignore` | Список файлов, которые не попадают в Git: `.env` (пароли), `node_modules`, `frontend/build`, `__pycache__`, `db.sqlite3`, `media/`, и т. д. |
| `.gitattributes` | Гарантирует переводы строк `LF` в репозитории (иначе Docker-скрипты с `CRLF` ломаются на Linux). |

### 2.2. `.github/workflows/main.yml` — CI/CD (GitHub Actions)

Запускается при каждом `push` в `main` и при pull request. Три задачи:

1. **tests** — ставит Python 3.11 и зависимости, запускает `flake8` (проверка PEP 8) и `manage.py test` (автотесты API).
2. **build_and_push_to_docker_hub** — после успешных тестов собирает образ бэкенда и публикует его как `<логин>/foodgram_backend:latest`.
3. **build_and_push_frontend_to_docker_hub** — то же самое для фронтенда: `<логин>/foodgram_frontend:latest`.

Публикация использует секреты репозитория `DOCKER_USERNAME` и `DOCKER_PASSWORD` (токен Docker Hub). Пароли в файле не хранятся.

---

### 2.3. `backend/` — серверная часть (Django)

```
backend/
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── manage.py
├── foodgram/      ← настройки проекта
├── users/         ← пользователи и подписки
├── recipes/       ← рецепты, ингредиенты, избранное, список покупок
└── api/           ← REST API (сериализаторы, представления, фильтры)
```

#### Корневые файлы

| Файл | Назначение |
|---|---|
| `Dockerfile` | Образ бэкенда: Python 3.11-slim → установка зависимостей → копирование кода. При старте выполняет миграции (`migrate`), собирает статику (`collectstatic`) и запускает Gunicorn на порту 8000. |
| `.dockerignore` | Что не копировать в образ (sqlite-база, media, кэш, venv). |
| `requirements.txt` | Зависимости с точными версиями: Django 4.2, DRF, Djoser, django-filter, Pillow (работа с картинками), Gunicorn, psycopg2 (драйвер PostgreSQL), python-dotenv (чтение `.env`). |
| `manage.py` | Стандартная точка входа Django: миграции, тесты, запуск сервера, пользовательские команды. |

#### `backend/foodgram/` — настройки проекта

| Файл | Назначение |
|---|---|
| `settings.py` | Главные настройки. Читает переменные из `infra/.env`. Если задан `POSTGRES_DB` — подключается к PostgreSQL, иначе использует SQLite (для локальной разработки). Подключает DRF с токен-аутентификацией, Djoser (вход по email), `django-filter`, пагинацию по 6 элементов. Статика Django отдаётся по `/backend_static/`, чтобы не пересекаться с `/static/` фронтенда. |
| `urls.py` | Корневые маршруты: `/admin/`, `/api/` и короткая ссылка `/s/<код>/`. |
| `wsgi.py` | Точка входа WSGI для Gunicorn. |
| `__init__.py` | Делает папку Python-пакетом. |

#### `backend/users/` — пользователи и подписки

| Файл | Назначение |
|---|---|
| `models.py` | `User` — свой пользователь (вход по email; обязательные имя и фамилия; необязательный аватар). `Subscription` — подписка пользователя на автора; запрещены дубли и подписка на самого себя (ограничения в БД). |
| `admin.py` | Админка: список пользователей, поиск по email и имени пользователя; админка подписок. |
| `migrations/0001_initial.py` | Миграция, создающая таблицы пользователей и подписок. |

#### `backend/recipes/` — рецепты

| Файл | Назначение |
|---|---|
| `models.py` | `Ingredient` (название, единица измерения), `Recipe` (автор, название, картинка, описание, время приготовления, дата публикации), `RecipeIngredient` (ингредиент в рецепте с количеством — «связующая» таблица), `Favorite` (избранное), `ShoppingCart` (список покупок). `Favorite` и `ShoppingCart` наследуются от общего абстрактного класса, чтобы не дублировать код. Пары «пользователь–рецепт» уникальны. |
| `admin.py` | Админка рецептов: в списке название и автор; поиск по названию и автору; на странице рецепта выводится, сколько раз его добавили в избранное; ингредиенты редактируются прямо в рецепте. Админка ингредиентов: название и единица измерения, поиск по названию. |
| `views.py` | Одна функция — переход по короткой ссылке `/s/<код>/` на страницу рецепта. Код — это номер рецепта в шестнадцатеричной системе, поэтому ссылка не меняется после редактирования. |
| `tests.py` | Автотесты API (10 штук): регистрация и вход, права доступа, создание/изменение/удаление рецепта, валидация, избранное, список покупок и суммирование, пагинация, подписки, аватар и смена пароля, поиск ингредиентов и короткая ссылка. |
| `migrations/0001_initial.py`, `0002_initial.py` | Миграции, создающие таблицы рецептов, ингредиентов и связей. |
| `management/commands/load_ingredients.py` | Команда: загружает 2186 ингредиентов из `data/ingredients.json`. |
| `management/commands/load_test_data.py` | Команда: создаёт 3 пользователей (`admin`, `ivan`, `maria`) и по одному рецепту. |
| `management/commands/load_demo_data.py` | Команда: создаёт 20 пользователей и 50 рецептов с картинками (подробнее в разделе 3). |

#### `backend/api/` — REST API

| Файл | Назначение |
|---|---|
| `urls.py` | Маршрутизатор: регистрирует `/users/`, `/ingredients/`, `/recipes/` и подключает вход/выход по токену (`/auth/token/login/`, `/auth/token/logout/`). |
| `views.py` | Вся логика API. `UserViewSet` — пользователи (Djoser) + аватар, подписки, подписаться/отписаться. `IngredientViewSet` — список и поиск ингредиентов. `RecipeViewSet` — CRUD рецептов, короткая ссылка, избранное, список покупок и скачивание списка файлом с суммированием ингредиентов. |
| `serializers.py` | Преобразование данных. `Base64ImageField` принимает картинку в виде строки base64 от фронтенда и сохраняет файл. Отдельные сериализаторы для чтения и записи рецепта (запись создаёт и обновляет ингредиенты в транзакции). |
| `filters.py` | Фильтры: поиск ингредиента по началу названия без учёта регистра; фильтр рецептов по автору, избранному и списку покупок. |
| `permissions.py` | Права: изменять и удалять рецепт может только его автор. |
| `pagination.py` | Пагинация: по 6 на страницу, число элементов задаётся параметром `limit`. |

---

### 2.4. `frontend/` — готовый клиент (React)

Дано заранее, в рамках проекта не менялось. Здесь только описание.

| Файл/папка | Назначение |
|---|---|
| `Dockerfile` | Собирает приложение (`npm install && npm run build`) на Node 21 и копирует результат в `build/`, после чего контейнер завершается. |
| `package.json`, `package-lock.json`, `yarn.lock` | Зависимости JavaScript. |
| `public/` | `index.html`, иконки, манифест. |
| `src/index.js`, `App.js` | Точка входа и корневой компонент с маршрутами. |
| `src/api/index.js` | Все запросы к бэкенду. |
| `src/pages/` | Страницы: главная, вход, регистрация, рецепт (`single-card`), создание и правка рецепта, автор (`user`), подписки, избранное, список покупок (`cart`), смена пароля, смена аватара, «О проекте» и «Технологии». |
| `src/components/` | Переиспользуемые части интерфейса: шапка, карточка рецепта, форма, поля ввода, пагинация, иконки и т. д. |
| `src/contexts/` | Контексты React: пользователь, авторизация, рецепты. |
| `src/utils/` | Вспомогательные хуки и валидация форм. |
| `src/fonts/`, `src/images/` | Шрифты и изображения интерфейса. |

---

### 2.5. `infra/` — инфраструктура

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | Описание всех четырёх контейнеров. `db` — PostgreSQL 13 с проверкой готовности (healthcheck); `backend` ждёт готовности БД; `frontend` собирает статику и завершается; `nginx` стартует после успешной сборки фронтенда. Три volume (`pg_data`, `static`, `media`) сохраняют данные при перезапусках. |
| `nginx.conf` | Правила nginx: `/api/docs/` → документация, `/api/` и `/admin/` и `/s/` → бэкенд, `/backend_static/` и `/media/` → файлы из volume, всё остальное → React (с возвратом `index.html` для маршрутов SPA). |
| `.env.example` | Образец файла настроек (`SECRET_KEY`, параметры PostgreSQL и т. д.). Копируется в `.env`, который в Git не попадает. |

### 2.6. `data/` — исходные данные

| Файл | Назначение |
|---|---|
| `ingredients.json`, `ingredients.csv` | Список из 2186 ингредиентов с единицами измерения. Загружается командой `load_ingredients`. |

### 2.7. `docs/` — документация API

| Файл | Назначение |
|---|---|
| `openapi-schema.yml` | Спецификация REST API (OpenAPI), по которой реализован бэкенд. |
| `redoc.html` | Страница, показывающая спецификацию; доступна на `/api/docs/`. |

### 2.8. `postman_collection/`

| Файл | Назначение |
|---|---|
| `foodgram.postman_collection.json` | Коллекция запросов для ручной проверки API в Postman. |
| `clear_db.sh`, `README.md` | Скрипт очистки БД между прогонами коллекции и описание. |

### 2.9. `task/`

Пять файлов `.docx` с исходными требованиями к проекту (возможности, стартовый набор и задание, план работы, подсказки, чек-листы сдачи).

---

## 3. Демонстрационные данные

В проекте три команды загрузки данных (выполняются по порядку; каждая безопасна при повторном запуске — дублей не создаёт):

| Команда | Что создаёт |
|---|---|
| `load_ingredients` | 2186 ингредиентов (обязательно первой). |
| `load_test_data` | Пользователи `admin` (суперпользователь), `ivan`, `maria` и по одному рецепту. |
| `load_demo_data` | 20 пользователей `user01`…`user20` и 50 рецептов от них. У каждого рецепта своя сгенерированная картинка и от 3 до 7 случайных ингредиентов. |

Запуск (из папки `infra`):

```bash
docker compose exec backend python manage.py load_ingredients --path /data/ingredients.json
docker compose exec backend python manage.py load_test_data
docker compose exec backend python manage.py load_demo_data
```

**Учётные записи** (пароль у всех — `Foodgram123`):

| Вход по email | Роль |
|---|---|
| `admin@foodgram.ru` | администратор (доступ в `/admin/`) |
| `ivan@foodgram.ru`, `maria@foodgram.ru` | обычные пользователи |
| `user01@foodgram.ru` … `user20@foodgram.ru` | обычные пользователи |

В итоге в базе: 23 пользователя и 53 рецепта (чтобы в списке было несколько страниц пагинации).

---

## 4. Как перенести проект на другую машину и запустить

### 4.1. Что нужно установить на новой машине

- **Docker Desktop** (Windows/macOS) или Docker Engine + Docker Compose (Linux). Больше ничего: ни Python, ни Node.js, ни PostgreSQL ставить не нужно.
- **Git** — если проект берётся из репозитория (вариант А).
- Свободный порт **80** (если занят — закройте программу, которая его использует, либо поменяйте `"80:80"` на `"8080:80"` в `infra/docker-compose.yml` и открывайте `http://localhost:8080`).
- Интернет при первом запуске: скачиваются базовые образы и пакеты, сборка фронтенда занимает несколько минут.

### 4.2. Вариант А — через Git (рекомендуется)

```bash
git clone https://github.com/Flexecstasy/Foodgram.git
cd Foodgram/infra
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
docker compose up -d --build
```

Дождитесь, пока команда завершится (в первый раз — 5–10 минут), затем загрузите данные:

```bash
docker compose exec backend python manage.py load_ingredients --path /data/ingredients.json
docker compose exec backend python manage.py load_test_data
docker compose exec backend python manage.py load_demo_data
```

Откройте: **http://localhost**. Документация API — http://localhost/api/docs/, админка — http://localhost/admin/ (вход: `admin@foodgram.ru` / `Foodgram123`).

> Если вы используете Git Bash на Windows и команда с `/data/...` выдаёт ошибку пути, выполните перед ней `export MSYS_NO_PATHCONV=1` или используйте PowerShell.

### 4.3. Вариант Б — без интернета и Git (копирование папкой)

1. На исходной машине скопируйте папку проекта целиком (флешка, архив). Папки `frontend/node_modules`, `frontend/build` и файл `infra/.env` копировать не нужно — они создаются заново.
2. На новой машине: установите Docker, откройте терминал в папке `infra` и выполните те же команды, что и в варианте А, начиная с `cp .env.example .env`.

Интернет всё равно нужен при первой сборке (скачиваются образы), если только вы не перенесли и Docker-образы командами `docker save` / `docker load`.

### 4.4. Вариант В — перенести уже готовую базу и картинки «как есть»

Нужно, если хотите, чтобы на новой машине были точно те же пользователи, рецепты и загруженные картинки, а не заново сгенерированные.

**На исходной машине** (в папке `infra`, контейнеры запущены):

```bash
docker compose exec -T db pg_dump -U foodgram_user -d foodgram > foodgram_dump.sql
docker compose cp backend:/app/media ./media_backup
```

Получатся файл `foodgram_dump.sql` и папка `media_backup`. Скопируйте их на новую машину (например, в папку `infra`). Пути указывайте относительные, как выше: Docker на Windows не понимает пути вида `/tmp/...`.

**На новой машине** (после шагов `git clone`, `cp .env.example .env` и `docker compose up -d --build`, но **без** загрузки данных):

```bash
# очистить схему и загрузить дамп
docker compose exec -T db psql -U foodgram_user -d foodgram -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec -T db psql -U foodgram_user -d foodgram < foodgram_dump.sql

# вернуть картинки
docker compose cp ./media_backup/. backend:/app/media

docker compose restart backend
```

> Значения `foodgram_user` и `foodgram` берутся из `infra/.env` (`POSTGRES_USER`, `POSTGRES_DB`). Если вы их меняли — подставьте свои.

### 4.5. Запуск готовых образов с Docker Hub (без сборки)

Образы уже опубликованы. Чтобы не собирать бэкенд и фронтенд на месте, в `infra/docker-compose.yml` для сервисов `backend` и `frontend` замените строку `build: ...` на:

```yaml
    image: svetlanaputana/foodgram_backend:latest     # для backend
    image: svetlanaputana/foodgram_frontend:latest    # для frontend
```

После этого `docker compose up -d` скачает образы вместо сборки.

### 4.6. Полезные команды

| Действие | Команда (в папке `infra`) |
|---|---|
| Посмотреть состояние контейнеров | `docker compose ps` |
| Логи бэкенда | `docker compose logs -f backend` |
| Остановить (данные сохранятся) | `docker compose down` |
| Остановить и удалить все данные | `docker compose down -v` |
| Создать своего суперпользователя | `docker compose exec backend python manage.py createsuperuser` |
| Запустить тесты | `docker compose exec backend python manage.py test` |

### 4.7. Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `port is already allocated` / порт 80 занят | Освободите порт 80 или поменяйте на `8080:80` в compose. |
| Страница пустая или 502 сразу после запуска | Бэкенд ещё стартует (миграции). Подождите 10–20 секунд и обновите страницу. |
| `failed to fetch anonymous token` при сборке | Временная проблема сети до Docker Hub — повторите `docker compose up -d --build`. |
| Сайт открывается, но нет рецептов | Не загружены данные — выполните три команды загрузки из раздела 4.2. |
| Docker Desktop не запускается | На Windows должен быть включён WSL2/виртуализация в BIOS. |

---

## 5. Как проект соответствует требованиям

| Требование | Где реализовано |
|---|---|
| PostgreSQL | `docker-compose.yml` (сервис `db`), `settings.py` |
| 4 контейнера: nginx, PostgreSQL, backend, frontend (только сборка) | `infra/docker-compose.yml` |
| Данные в volumes | `pg_data`, `static`, `media` |
| `requirements.txt` | `backend/requirements.txt` |
| Образы на Docker Hub | `.github/workflows/main.yml` |
| CI/CD на GitHub Actions | `.github/workflows/main.yml` |
| Токен-аутентификация, вход по email | `settings.py` (Djoser, `LOGIN_FIELD = email`) |
| Пагинация, сортировка «новые выше» | `api/pagination.py`, `Recipe.Meta.ordering` |
| Суммирование ингредиентов в списке покупок | `api/views.py` → `download_shopping_cart` |
| Короткая ссылка рецепта | `api/views.py` → `get_link`, `recipes/views.py` |
| Админка с поиском и счётчиком избранного | `recipes/admin.py`, `users/admin.py` |
| Тестовые данные | команды `load_test_data` и `load_demo_data` |
| PEP 8 | `setup.cfg`, шаг flake8 в CI |
