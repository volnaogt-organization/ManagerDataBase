"""
HTTP-сервис ManagerDataBase — модульная обёртка для ReportPalette.

Запускается внутри контейнера модуля:
    uvicorn service.api:app --host 0.0.0.0 --port 8000

Контракт модуля ReportPalette:
    GET  /health    -> {"status": "ok", "module": ..., "version": ...}
    GET  /manifest  -> содержимое module.json из корня репозитория
    POST /run, /annual_plan, ... — рабочие эндпоинты модуля

Версия модуля приходит из переменной окружения MODULE_VERSION
(проставляется Docker-сборкой из git-тега релиза).
"""

import json
import os
import threading
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scr.manager_database import MainLogic

MODULE_NAME = "managerdatabase"
MODULE_VERSION = os.environ.get("MODULE_VERSION", "dev")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="ManagerDataBase module",
    description="Сервис-обёртка над логикой ManagerDataBase для ReportPalette",
    version=MODULE_VERSION,
)

# Внутри docker-сети ReportPalette запросы идут от шлюза; CORS — на случай прямых обращений при отладке.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Обработка ДСЕ идёт в одном экземпляре логики; блокировка защищает от параллельных запусков
_lock = threading.Lock()


class RunRequest(BaseModel):
    program: int = Field(..., description="Отчёт: 1010 или 2012")
    dse_list: List[str] = Field(default_factory=list,
                                description="Список ДСЕ, напр. ['ЛТИЯ.716713.001']")
    save_input: int = Field(0, description="1 — сохранить результат в Excel")
    max_threads: int = Field(6, ge=1, le=16)


class ExcelJobRequest(BaseModel):
    path_to_excel_file: str


@app.get("/health")
def health():
    return {"status": "ok", "module": MODULE_NAME, "version": MODULE_VERSION}


@app.get("/manifest")
def manifest():
    """Манифест модуля (module.json из корня репозитория)."""
    path = os.path.join(REPO_ROOT, "module.json")
    if not os.path.isfile(path):
        raise HTTPException(404, "module.json не найден в контейнере модуля")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _run_locked(fn, *args, **kwargs):
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, "Уже выполняется другая задача, попробуйте позже")
    try:
        return fn(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка при обработке: {e}")
    finally:
        _lock.release()


@app.post("/run")
def run(req: RunRequest):
    """Обработка списка ДСЕ отчётом 1010 или 2012."""
    if req.program not in (1010, 2012):
        raise HTTPException(400, "program должен быть 1010 или 2012 "
                                 "(файловые программы: /annual_plan, /queue_management, /sz_notifications)")
    if not req.dse_list:
        raise HTTPException(400, "Пустой список ДСЕ")

    def job():
        MainLogic().start_generate_report_database_volna(
            dse_list=req.dse_list,
            user_selected_program=req.program,
            save_input=req.save_input,
            max_threads=req.max_threads,
        )
        return {"status": "done", "program": req.program, "processed": len(req.dse_list)}

    return _run_locked(job)


def _excel_job(req: ExcelJobRequest, program: int):
    if not os.path.isfile(req.path_to_excel_file):
        raise HTTPException(400, f"Файл не найден: {req.path_to_excel_file}")

    def job():
        if program == 4:
            MainLogic().start_semi_automatic_update_report(
                path_to_excel_file=req.path_to_excel_file,
                user_selected_program=4,
            )
        else:
            # 365 — годовой план; 3 — УП по очередям
            MainLogic.start_copy_report(
                path_to_excel_file=req.path_to_excel_file,
                user_selected_program=program,
            )
        return {"status": "done", "program": program}

    return _run_locked(job)


@app.post("/annual_plan")
def annual_plan(req: ExcelJobRequest):
    """Загрузка годового отчёта (365) из Excel-файла."""
    return _excel_job(req, 365)


@app.post("/queue_management")
def queue_management(req: ExcelJobRequest):
    """УП по очередям (3) из Excel-файла."""
    return _excel_job(req, 3)


@app.post("/sz_notifications")
def sz_notifications(req: ExcelJobRequest):
    """ДСЕ по СЗ и извещениям (4) из Excel-файла."""
    return _excel_job(req, 4)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
