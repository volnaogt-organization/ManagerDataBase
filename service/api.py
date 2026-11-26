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
from scr.handler.handlers_excel.handler_reader_excel import DataAcquisition, ReaderExcelColumn

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


class ExcelSheetsRequest(BaseModel):
    path: str


class ExcelColumnsRequest(BaseModel):
    path: str
    sheet: str


class ExcelDseColumnRequest(BaseModel):
    path: str
    sheet: str
    column_index: int = Field(..., ge=1, description="Номер столбца, начиная с 1")


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


# ---------- Чтение Excel: листы, столбцы, ДСЕ из столбца ----------

def _check_excel(path: str):
    path = (path or "").strip().strip('"').strip("'")
    if not path or not os.path.isfile(path):
        raise HTTPException(400, f"Файл не найден: {path}")
    return path


@app.post("/excel/sheets")
def excel_sheets(req: ExcelSheetsRequest):
    """Список листов Excel-файла."""
    path = _check_excel(req.path)
    try:
        return {"sheets": DataAcquisition(path).get_list_excel_file()}
    except Exception as e:
        raise HTTPException(500, f"Не удалось прочитать файл: {e}")


@app.post("/excel/columns")
def excel_columns(req: ExcelColumnsRequest):
    """Заголовки столбцов указанного листа."""
    path = _check_excel(req.path)
    try:
        headers = DataAcquisition(path).get_headers(name_list=req.sheet)
        columns = [
            {"index": i + 1, "name": str(h) if h is not None and str(h).strip() else f"Столбец {i + 1}"}
            for i, h in enumerate(headers)
        ]
        return {"columns": columns}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Не удалось прочитать столбцы: {e}")


@app.post("/excel/dse_column")
def excel_dse_column(req: ExcelDseColumnRequest):
    """Список ДСЕ из столбца Excel (без пустых и повторов, как в cmd_body)."""
    path = _check_excel(req.path)
    try:
        data = ReaderExcelColumn(
            path_to_excel_file=path,
            name_sheet=req.sheet,
        ).get_data_column([req.column_index])

        values = next(iter(data.values()), [])
        dse_list = list(dict.fromkeys(str(v).strip() for v in values if v is not None and str(v).strip()))
        if not dse_list:
            raise HTTPException(400, "В выбранном столбце нет значений")
        return {"dse_list": dse_list, "count": len(dse_list)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Не удалось прочитать столбец: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
