# Архитектура ManagerDataBase

## Обзор

ManagerDataBase — программа создания и обновления базы данных производственных
отчётов. Программа работает с двумя источниками данных:

* **Microsoft SQL Server** (через `pyodbc` + SQLAlchemy, Windows-аутентификация
  `Trusted_Connection`) — исходные производственные отчёты **1010** и **2012**
  по ДСЕ;
* **общая SQLite-база** (`report_table.db`, расположена на сетевом ресурсе) —
  накопительная база результатов, включая годовое планирование, УП по очередям
  и ДСЕ по СЗ/извещениям.

Продукт распространяется в двух режимах:

1. **CLI** — консольное меню (`scr/cmd_body.py`);
2. **HTTP-модуль ReportPalette** — FastAPI-сервис (`service/api.py`) в
   Docker-контейнере.

## Структура репозитория

```
ManagerDataBase/
├── module.json          # манифест модуля ReportPalette (версия, команды UI, эндпоинты)
├── requirements.txt     # Python-зависимости
├── Dockerfile           # образ модуля (python:3.12-slim + msodbcsql18)
├── .github/workflows/   # CI: релиз (тег v* -> GitHub Release + образ в GHCR)
│
├── service/
│   └── api.py           # HTTP-обёртка над ядром (FastAPI), контракт модуля
│
├── scr/                 # ядро программы
│   ├── manager_database.py        # MainLogic: оркестрация потоковой обработки ДСЕ
│   ├── cmd_body.py                # консольное меню (CLI-режим)
│   │
│   ├── handler/                   # обработчики источников (SQL Server / Excel)
│   │   ├── handlers_db/
│   │   │   ├── assets_1010.py     # Header1010  — выборка отчёта 1010 по одному ДСЕ
│   │   │   └── assets_2012.py     # Header2012  — выборка отчёта 2012 по одному ДСЕ
│   │   ├── handlers_excel/
│   │   │   └── handler_reader_excel.py  # DataAcquisition, ReaderExcelColumn — чтение Excel
│   │   ├── annual_plan.py         # HandlerAnnualPlan      (программа 365)
│   │   ├── queue_management.py    # HandlerQueueManagement (программа 3)
│   │   └── sz_notifications.py    # HandlerSzNotifications (программа 4)
│   │
│   ├── database_assets/           # слой записи в SQLite
│   │   ├── receiver_sqlite_database.py  # SQLiteManager: UPSERT по схеме/unique-ключам
│   │   └── handling_database/     # схемы таблиц и логика обновления для каждой программы
│   │       ├── handler_report_1010.py
│   │       ├── handler_report_2012.py
│   │       ├── handler_annual_plan.py
│   │       ├── handler_queue_management.py
│   │       └── handler_sz_notifications.py
│   │
│   ├── excel_assets/              # вывод результатов в Excel
│   │   ├── enters/excel_enter.py          # ExcelDataInserter (openpyxl)
│   │   └── readers/                        # быстрые читатели строк/ячеек (pandas/openpyxl/xlrd)
│   │
│   └── config_assets/             # конфигурация
│       ├── receiver_config.py             # ReceiverConfig: ~/.config/.ManagerDataBase/config.json
│       └── handling_config/handler_program_config.py
│
├── static/
│   └── config.py        # базовая конфигурация программы (configProgram)
└── test/                # вспомогательные скрипты
```

## Поток данных

### Отчёты 1010 / 2012 (список ДСЕ)

```
dse_list ──> MainLogic.start_generate_report_database_volna()
                 │  ThreadPoolExecutor(max_threads)
                 ▼
             _process_single_dse(дсе)          # свой экземпляр обработчика на поток
                 │  pyodbc / SQLAlchemy ──> MS SQL Server
                 ▼
             результат {дсе: данные}
                 │  (save_input=1)
                 ▼
             result_manager_database_reports.xlsx  (лист rep-<program> date-<дд.мм.гггг>)
             + обновление SQLite (handler_report_1010 / handler_report_2012)
```

Ключевые свойства:

* обработка изолирована по ДСЕ: ошибка одного элемента не прерывает волну;
* параллельность ограничена (`max_threads` 1..16, по умолчанию 6);
* на уровне HTTP-сервиса все задачи сериализуются мьютексом (см. `docs/API.md`).

### Файловые программы (3, 4, 365)

```
Excel-файл ──> Handler*().main(path)  ──> SQLiteManager (UPSERT в report_table.db)
                                    └──> (программа 3) выгрузка в лист QM <дата>
```

* **365** — загрузка годового плана из Excel в базу;
* **3** — УП по очередям: обновление базы + экспорт результата в Excel;
* **4** — ДСЕ по СЗ и извещениям: полуавтоматическое обновление по списку файлов.

## Слой хранения

### SQLiteManager (`scr/database_assets/receiver_sqlite_database.py`)

Универсальный менеджер SQLite, работающий по переданной конфигурации:

* `schema` — словарь `{колонка: SQL-тип}`;
* `unique_keys` — колонки для `UNIQUE`, используются в UPSERT
  (`INSERT ... ON CONFLICT DO UPDATE`);
* `indexes` — дополнительные индексы;
* соединения потокобезопасны (`check_same_thread=False`), PRAGMA:
  `journal_mode=MEMORY`, `synchronous=NORMAL`, `cache_size=64 МБ`.

Файл базы по умолчанию:
`\\volna.dmn\data\...\database_program\report_table.db` (сетевой ресурс; путь
задаётся конструктором соответствующего `handler_*`).

### MS SQL Server (`scr/handler/handlers_db/assets_*.py`)

Подключение через `pyodbc`: выбирается доступный драйвер с «SQL Server» в
названии (в Docker-образе предустановлен `msodbcsql18`), строка соединения —
`Trusted_Connection=yes` (Windows-аутентификация). Для локального запуска вне
домена необходим рабочий ODBC-доступ к серверу.

## Конфигурация

* `static/config.py` — встроенные значения по умолчанию (`configProgram`).
* `ReceiverConfig` — пользовательский конфиг в
  `~/.config/.ManagerDataBase/config.json`; при первом запуске создаётся из
  значений по умолчанию, поддерживает миграцию из старого расположения
  `~/.ManagerDataBase`.
* `MODULE_VERSION` — версия модуля из окружения (проставляется сборкой из
  git-тега).

## Интеграция с ReportPalette

Манифест `module.json` описывает:

* API-контракт: порт 8000, `/health`, `/manifest`;
* возможности: отчёты `[1010, 2012]`, Excel-задачи `[3, 4, 365]`;
* команды UI (7 команд): ручной ввод ДСЕ (через `$` или `;`), выбор столбца
  ДСЕ из Excel, три файловые команды; каждая указывает endpoint, payload и
  ожидаемый результат `result_manager_database_reports.xlsx`.

Релизный цикл: пуш тега `v*` → GitHub Actions собирает Docker-образ
(`ghcr.io/<org>/managerdatabase:<tag>` и `:latest`) и создаёт GitHub Release
(`.github/workflows/release.yml`).
