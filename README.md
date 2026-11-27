# ManagerDataBase

Программа для создания и обновления базы данных производственных отчётов:
обработка отчётов **1010** и **2012** по спискам ДСЕ, загрузка годового плана
(365), УП по очередям (3), ДСЕ по СЗ и извещениям (4).

Работает в двух режимах:

* **CLI** — консольное меню (`scr/cmd_body.py`);
* **HTTP-сервис** — модуль платформы ReportPalette (FastAPI, Docker).

## Возможности

| Программа | Что делает | Источник | Режимы |
|-----------|------------|----------|--------|
| 1010 | Отчёт 1010 по списку ДСЕ | MS SQL Server | список ДСЕ вручную / из столбца Excel |
| 2012 | Отчёт 2012 по списку ДСЕ | MS SQL Server | список ДСЕ вручную / из столбца Excel |
| 365 | Загрузка годового отчёта | Excel → SQLite | файл |
| 3 | УП по очередям | Excel → SQLite + Excel-результат | файл |
| 4 | ДСЕ по СЗ и извещениям | Excel → SQLite | файл |

Результаты обработок 1010/2012/3 при `save_input=1` сохраняются в
`result_manager_database_reports.xlsx` в текущей директории.

## Быстрый старт

### Требования

* Python 3.12+
* Доступ к MS SQL Server (отчёты 1010/2012) и к сетевому ресурсу с общей
  SQLite-базой `report_table.db`
* Для Docker-сборки — ODBC-драйвер `msodbcsql18` (уже включён в Dockerfile)

### Установка

```bash
git clone <repo-url> && cd ManagerDataBase
pip install -r requirements.txt
```

### Запуск CLI

```bash
python scr/cmd_body.py
```

В меню выберите программу (1 — 1010, 2 — 2012, 3 — УП по очередям,
4 — ДСЕ по СЗ, 365 — годовой отчёт) и введите данные: список ДСЕ через `$`
или `;`, либо путь к Excel-файлу.

### Запуск HTTP-сервиса

Локально:

```bash
uvicorn service.api:app --host 0.0.0.0 --port 8000
```

В Docker:

```bash
docker build -t managerdatabase:dev .
docker run -p 8000:8000 managerdatabase:dev
```

Проверка:

```bash
curl http://localhost:8000/health
# {"status":"ok","module":"managerdatabase","version":"dev"}
```

Swagger UI доступен на `http://localhost:8000/docs`.

Пример запроса:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"program": 1010, "dse_list": ["ЛТИЯ.716713.001"], "save_input": 1}'
```

## Релизы

Сборка и публикация образа выполняются GitHub Actions при пуше тега:

```bash
git tag v0.5.3
git push origin v0.5.3
```

Результат: GitHub Release + образы
`ghcr.io/<организация>/managerdatabase:v0.5.3` и `:latest`
(см. `.github/workflows/release.yml`). Версия попадает в контейнер через
переменную окружения `MODULE_VERSION`.

## Структура проекта

```
├── module.json      # манифест модуля ReportPalette (команды UI, эндпоинты)
├── service/api.py   # FastAPI-сервис (HTTP-обёртка над ядром)
├── scr/             # ядро: MainLogic, обработчики БД/Excel, конфиги
├── static/config.py # значения конфигурации по умолчанию
├── Dockerfile       # образ модуля (python:3.12-slim + msodbcsql18)
├── test/            # вспомогательные скрипты
└── docs/            # документация
```

## Документация

* [docs/API.md](docs/API.md) — справочник HTTP API (эндпоинты, схемы запросов, коды ошибок)
* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — архитектура, потоки данных, слои хранения и конфигурация

## Лицензия

Внутренний проект. Использование — только внутри организации.
