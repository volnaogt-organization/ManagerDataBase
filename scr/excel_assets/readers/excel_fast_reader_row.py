"""
Быстрый читатель Excel-файлов (.xls / .xlsx).
Приоритет — скорость чтения. Логика цветов ячеек удалена.
Рекомендуется: pip install python-calamine  (ускорение чтения xlsx/xlsm в 5-10 раз)
"""
import traceback

import xlrd
import pandas as pd

from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Hashable

try:
    import python_calamine  # noqa: F401  — регистрирует движок "calamine" в pandas
    _FAST_ENGINE = "calamine"
except ImportError:
    _FAST_ENGINE = None

# Регулярка для подсчёта кириллических символов (используется в fix_dataframe_encoding)
_CYRILLIC = r"[А-Яа-яЁё]"


class ExcelReader:
    """Читает первый подходящий лист Excel-файла с автоопределением формата
    и исправлением кодировки (cp1252->cp1251)."""

    ENCODINGS = ["cp1251", "utf-8", "cp866", "koi8_r", "iso-8859-5"]

    def __init__(
        self,
        file_path: str,
        sheet_name: Optional[Union[str, int]] = None,
        track_sheet_origin: bool = False,
        encoding: Optional[str] = None,
        header_row: int = 0,
        skip_sheet: Optional[Union[str, int, List[Union[str, int]]]] = None,
    ):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.encoding = encoding
        self.header_row = header_row
        self.data: Optional[pd.DataFrame] = None
        self.columns_save: List[str] = []
        self.filtered_data: Optional[Dict[int, Dict[str, Any]]] = None
        self.track_sheet_origin = track_sheet_origin
        self.sheet_origin: Optional[str] = None
        self.skip_sheet = skip_sheet

        self.load_excel()

    # ---------- кодировка (векторизовано) ----------

    @staticmethod
    def fix_encoding(text: Any) -> Any:
        if not isinstance(text, str):
            return text
        try:
            return text.encode("cp1252", errors="ignore").decode("cp1251", errors="ignore")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    @staticmethod
    def fix_dataframe_encoding(df: pd.DataFrame) -> pd.DataFrame:
        """
        Чинит «кракозябры» (cp1252 -> cp1251) только там, где после
        перекодировки появляется больше кириллицы, чем было.
        """
        obj_cols = df.select_dtypes(include="object").columns
        if len(obj_cols) == 0:
            return df

        df = df.copy()
        for col in obj_cols:
            s = df[col].astype("string")
            fixed = s.str.encode("cp1252", errors="ignore").str.decode("cp1251", errors="ignore")

            fc = fixed.str.count(_CYRILLIC).astype("float64").fillna(0.0)
            sc = s.str.count(_CYRILLIC).astype("float64").fillna(0.0)
            gained = (fc > sc).fillna(False)  # обычный bool, без pd.NA

            df[col] = fixed.where(gained, s).astype("object")
        return df

    # ---------- вспомогательное ----------

    @staticmethod
    def _detect_format(file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".xls":
            return "xls"
        if ext in (".xlsx", ".xlsm"):
            return "xlsx"
        with open(file_path, "rb") as f:
            header = f.read(8)
        if header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return "xls"
        if header[:4] == b"PK\x03\x04":
            return "xlsx"
        raise ValueError(f"Неизвестный формат файла: {file_path}")

    def _should_skip_sheet(self, sheet_name: str, sheet_index: int) -> bool:
        if self.skip_sheet is None:
            return False
        skip_list = self.skip_sheet if isinstance(self.skip_sheet, list) else [self.skip_sheet]
        return any(
            (isinstance(item, int) and sheet_index == item)
            or (isinstance(item, str) and sheet_name == item)
            for item in skip_list
        )

    @staticmethod
    def _apply_header(df: pd.DataFrame, header_row: int) -> pd.DataFrame:
        """Делает строку header_row заголовками; header_row=None — без заголовков."""
        if header_row is None:
            return df
        if header_row >= len(df):
            print(f"[ExcelReader] WARNING: header_row={header_row} >= числа строк ({len(df)}). "
                  f"Сбрасываем в 0.")
            header_row = 0
        headers = list(df.iloc[header_row])
        headers = [h if isinstance(h, str) and h.strip() else f"Unnamed: {i}"
                   for i, h in enumerate(headers)]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df.columns = headers
        return df


    def load_excel(
        self,
        file_path: Optional[str] = None,
        sheet_name: Optional[Union[str, int]] = None,
        encoding: Optional[str] = None,
        skip_sheet: Optional[Union[str, int, List[Union[str, int]]]] = None,
    ) -> Optional[pd.DataFrame]:
        path = file_path or self.file_path
        sheet = sheet_name if sheet_name is not None else self.sheet_name
        enc = encoding or self.encoding

        if skip_sheet is not None:
            self.skip_sheet = skip_sheet

        try:
            if self._detect_format(path) == "xls":
                df = self._load_xls(path, sheet, enc)
            else:
                df = self._load_xlsx(path, sheet)

            df = self.fix_dataframe_encoding(df)

            if self.track_sheet_origin and self.sheet_origin is not None:
                df["__sheet_origin__"] = self.sheet_origin

            if file_path is None and sheet_name is None:
                self.data = df
            return df

        except Exception as e:
            traceback.print_exc()  # покажет точную строку ошибки
            print(f"Ошибка при загрузке файла или листа: {e}")
            if file_path is None and sheet_name is None:
                self.data = None
            return None

    def _load_xls(self, path: str, sheet: Optional[Union[str, int]],
                  encoding: Optional[str]) -> pd.DataFrame:
        """.xls через xlrd: определение кодировки, выбор листа, чтение за один проход."""
        used_encoding = None
        workbook = None
        errors = []

        candidates = [encoding] if encoding else list(self.ENCODINGS)
        candidates.append(None)  # автоопределение xlrd

        for enc in candidates:
            try:
                workbook = xlrd.open_workbook(path, encoding_override=enc) if enc \
                    else xlrd.open_workbook(path)
                used_encoding = enc or "auto"
                break
            except Exception as e:
                errors.append(f"{enc}: {e}")

        if workbook is None:
            raise ValueError(f"Не удалось открыть .xls файл. Ошибки: {errors[-1]}")

        sheet_names = workbook.sheet_names()
        workbook.release_resources()  # метаданные получены, файл можно закрыть

        if sheet is not None:
            if isinstance(sheet, int):
                target = sheet_names[sheet]
            else:
                target = sheet
        else:
            target = next(
                (name for idx, name in enumerate(sheet_names)
                 if not self._should_skip_sheet(name, idx)),
                None,
            )
            if target is None:
                raise ValueError(f"Все листы исключены (skip_sheet={self.skip_sheet}).")

        self.sheet_origin = target
        return self._read_with_engine(path, target, engine="xlrd",
                                      encoding_override=used_encoding if used_encoding != "auto" else None)

    def _load_xlsx(self, path: str, sheet: Optional[Union[str, int]]) -> pd.DataFrame:
        engine = _FAST_ENGINE or "openpyxl"
        if sheet is not None:
            self.sheet_origin = sheet if isinstance(sheet, str) else None
            return self._read_with_engine(path, sheet, engine=engine)

        # sheet=None: выбрать первый не исключённый лист
        names = pd.ExcelFile(path, engine=engine).sheet_names
        target = next(
            (name for idx, name in enumerate(names) if not self._should_skip_sheet(name, idx)),
            None,
        )
        if target is None:
            raise ValueError(f"Все листы исключены (skip_sheet={self.skip_sheet}).")
        self.sheet_origin = target
        return self._read_with_engine(path, target, engine=engine)

    def _read_with_engine(self, path, sheet, engine, encoding_override=None) -> pd.DataFrame:
        """Читает лист за один проход: header=None, затем заголовок применяем в памяти."""
        kwargs = {"engine": engine, "header": None}
        if encoding_override:
            kwargs["encoding_override"] = encoding_override
        df = pd.read_excel(path, sheet_name=sheet, **kwargs)
        df = self._apply_header(df, self.header_row)
        return df


    def get_dict_all_data(self) -> Dict[int, Dict[str, Any]]:
        if self.data is None:
            return {}
        return {index: row.to_dict() for index, row in self.data.iterrows()}

    def get_headers(self) -> List[str]:
        return list(self.data.columns) if self.data is not None else []

    def filter_and_save_columns(self, columns_to_save: Union[str, List[str], tuple]):
        if self.data is None:
            return
        if isinstance(columns_to_save, str):
            columns_to_save = [columns_to_save]
        self.columns_save = list(columns_to_save)
        self.filtered_data = {
            index: {col: row[col] for col in self.columns_save if col in row}
            for index, row in self.data.iterrows()
        }

    def get_filtered_data(self):
        return self.filtered_data

    @staticmethod
    def is_empty(val: Any) -> bool:
        return (val is None or
                (isinstance(val, str) and val.strip().lower() in ("", "nan", "n/a", "none", "-", "null")) or
                pd.isna(val))

    def get_column_values(self, get_column: str, foc_mode: bool = False,
                          skip_condition: Optional[callable] = None) -> List[str]:
        if get_column not in self.columns_save:
            return []
        result = []

        for key, row in (self.filtered_data or {}).items():
            if foc_mode and skip_condition is not None:
                if skip_condition(self.data.loc[key]):  # передаём строку, без полного словаря
                    continue
            value = row.get(get_column)
            if value is None or self.is_empty(value):
                continue
            for item in str(value).strip().replace(", ", "|").split("|"):
                item = item.strip()
                if not item:
                    continue
                if ":" in item and "-" in item:
                    item = item[:len(item) // 2 + 1]
                if item not in result:
                    result.append(item)

        result.sort(reverse=True)
        result.append("")
        return result

    def return_data(self) -> Optional[pd.DataFrame]:
        return self.data


class MultiSheetReader:
    """Читает несколько листов из одного Excel-файла одним проходом."""

    def __init__(self, file_path: str,
                 skip_sheets: Optional[Union[str, int, List[Union[str, int]]]] = None):
        self.file_path = file_path
        self.sheets: Dict[str, pd.DataFrame] = {}
        self.skip_sheets = skip_sheets

    def _should_skip(self, sheet_name: str, sheet_index: int) -> bool:
        if self.skip_sheets is None:
            return False
        skip_list = self.skip_sheets if isinstance(self.skip_sheets, list) else [self.skip_sheets]
        return any(
            (isinstance(item, int) and sheet_index == item)
            or (isinstance(item, str) and sheet_name == item)
            for item in skip_list
        )

    def load_sheets(self, sheet_names: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Один проход по файлу: читает все листы разом (sheet_name=None)."""
        try:
            engine = _FAST_ENGINE or None  # None = движок по умолчанию pandas
            all_data = pd.read_excel(self.file_path, sheet_name=None, engine=engine)
        except Exception as e:
            traceback.print_exc()
            print(f"Ошибка при открытии файла: {e}")
            return {}

        names = list(all_data.keys())
        for idx, name in enumerate(names):
            if sheet_names is not None and name not in sheet_names:
                continue
            if self._should_skip(name, idx):
                continue
            try:
                self.sheets[name] = ExcelReader.fix_dataframe_encoding(all_data[name])
            except Exception as e:
                traceback.print_exc()
                print(f"Ошибка при загрузке листа {name}: {e}")

        return self.sheets

    def get_sheet_as_dict(self, sheet_name: str) -> Optional[Dict[Hashable, dict]]:
        data = self.sheets.get(sheet_name)
        return {i: r.to_dict() for i, r in data.iterrows()} if data is not None else None

    def get_sheet(self, sheet_name: str) -> Optional[pd.DataFrame]:
        return self.sheets.get(sheet_name)