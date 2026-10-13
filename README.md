# Фудграм

Сайт, на котором пользователи публикуют рецепты, добавляют чужие рецепты в избранное,
подписываются на авторов и формируют список покупок (с суммированием ингредиентов).

Стек: Python 3.11, Django 4.2, Django REST Framework, Djoser (токен-авторизация),
PostgreSQL, Gunicorn, Nginx, Docker Compose, GitHub Actions. Фронтенд — готовое React SPA.

## Структура

- `backend/` — Django-проект: приложения `users` (пользователи, подписки), `recipes`
  (рецепты, ингредиенты, избранное, список покупок), `api` (сериализаторы, вьюсеты, фильтры).
- `frontend/` — SPA, `infra/` — nginx и docker-compose, `data/` — ингредиенты, `docs/` — спецификация API.

## Запуск в Docker (для ревьюера)

1. `cd infra && cp .env.example .env` (при необходимости поменяйте значения).
2. `docker compose up -d --build` — поднимутся `db`, `backend`, `nginx`; контейнер `frontend`
   только собирает статику фронтенда и завершается.
3. Загрузите данные:
   ```
   docker compose exec backend python manage.py load_ingredients --path /data/ingredients.json
   docker compose exec backend python manage.py load_test_data
   docker compose exec backend python manage.py load_demo_data   # +20 пользователей, +50 рецептов
   docker compose exec backend python manage.py createsuperuser   # при желании
   ```
4. Сайт: http://localhost/, API: http://localhost/api/, документация: http://localhost/api/docs/,
   админка: http://localhost/admin/.

`load_test_data` создаёт пользователей `admin` (суперпользователь), `ivan`, `maria`
(пароль у всех `Foodgram123`) и по одному рецепту от каждого. `load_demo_data` добавляет
пользователей `user01`…`user20` и 50 рецептов с картинками. Подробное описание проекта и
инструкция по переносу на другую машину — в `PROJECT_GUIDE.md`.

Данные хранятся в volumes (`pg_data`, `static`, `media`). Статика Django (админка) раздаётся
по адресу `/backend_static/`, чтобы не пересекаться с `/static/` фронтенда.

## Локальная разработка (SQLite)

```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_ingredients
python manage.py load_test_data
python manage.py runserver
```

Тесты: `python manage.py test`. Проверка стиля: `flake8 --config setup.cfg backend`.

## CI/CD

GitHub Actions (`.github/workflows/main.yml`): flake8 и тесты на каждый push/PR, при push в `main`
образы бэкенда и фронтенда собираются и публикуются на Docker Hub
(`<DOCKER_USERNAME>/foodgram_backend`, `<DOCKER_USERNAME>/foodgram_frontend`).
Нужны секреты репозитория `DOCKER_USERNAME` и `DOCKER_PASSWORD`.

## Особенности реализации

- Вход по email и паролю: `POST /api/auth/token/login/`, далее заголовок `Authorization: Token <token>`.
- Пагинация: 6 рецептов на странице, параметры `page` и `limit`.
- Список покупок скачивается как `.txt`, ингредиенты суммируются.
- Короткая ссылка рецепта `/s/<id в hex>/` перенаправляет на страницу рецепта и не меняется при редактировании.
