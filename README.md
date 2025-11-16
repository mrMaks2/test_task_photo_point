# Система уведомлений

## Описание

Данный проект представляет собой микросервис для управления и отправки уведомлений через multiple каналы (email, SMS, Telegram). Система обеспечивает отказоустойчивую доставку сообщений с поддержкой приоритетов, повторных попыток и планирования отправки.


## Используемые технологии

*   **Python:** Язык программирования.
*   **Djangon:** HTTP-фреймворк.
*   **PostgreSQL:** База данных.
*   **Docker и Docker Compose:** Для контейнеризации.
*   **Celery + Redis:** Для очереди задач (планирование).
*   **Каналы доставки:** Email: SMTP (поддержка Gmail); SMS: Twilio API; Мессенджеры: Telegram Bot API.

## Инструкция по запуску приложения

1.  **Убедитесь, что у вас установлен Docker и Docker Compose.**

2.  **Создайте файл .env на основе примера.**

    ```bash
    cp .env.example .env
    ```

3.  **Склонируйте репозиторий:**

    ```bash
    git clone https://github.com/mrMaks2/test_task_photo_point.git
    ```

4.  **Запустите проект с помощью команды:**

    ```bash
    docker-compose up --build
    ```

5.  **После запуска контейнеров, выполните миграции для применения изменений в базе данных:**

    ```bash
    docker-compose exec web python manage.py migrate
    ```

6.  **Создание суперпользователя:**

    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

7.  **Проведение тестов:**

    ```bash
    docker-compose exec web python manage.py test tests --verbosity=2
    ```

8.  **Проверка работоспособности:**

    *   **API:** http://localhost:8000/api/v1/notifications/
    *   **Админ-панель:** http://localhost:8000/admin/
    *   **Статистика:** http://localhost:8000/api/v1/notifications/stats/

## API Endpoints

*   **GET /api/v1/notifications/** - список уведомлений.
*   **POST /api/v1/notifications/** - создание уведомления.
*   **GET /api/v1/notifications/{id}/** - детали уведомления.
*   **POST /api/v1/notifications/{id}/retry/** - повторная отправка.
*   **GET /api/v1/notifications/stats/** - статистика доставки.