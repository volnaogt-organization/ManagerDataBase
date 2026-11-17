import xlrd
import openpyxl
import pandas as pd

from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Hashable, Tuple


class ExcelReader:
    """
    Базовый класс для чтения Excel-файлов.
    Автоматически определяет формат (.xls / .xlsx) и использует правильный парсер.
    Для старых .xls файлов использует xlrd с поддержкой кодировок Windows-1251/CP866.

    Результат работы — словарь вида:
    {
        row_idx: {
            name_column: [cell_value, cell_color],
            ...
        },
        ...
    }
    где cell_color — hex-строка ('#RRGGBB') или None, если заливки нет.
    row_idx — индекс строки DataFrame (0, 1, 2, ...).
    """

    ENCODINGS = ["cp1251", "utf-8", "cp866", "koi8_r", "iso-8859-5"]

    def __init__(
            self
            , file_path: str
            , sheet_name: Optional[Union[str, int]] = None
            , color_filter_column: Optional[str] = None
            , track_sheet_origin: bool = False
            , encoding: Optional[str] = None
            , header_row: int = 0
            , skip_sheet: Optional[Union[str, int, List[Union[str, int]]]] = None
    ):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.encoding = encoding
        self.header_row = header_row
        self.effective_header = 0
        self.data: Optional[pd.DataFrame] = None
        self.columns_save: List[str] = []
        self.filtered_data: Optional[Dict[int, Dict[str, Any]]] = None
        self.color_filter_column = color_filter_column
        self.track_sheet_origin = track_sheet_origin
        self.sheet_origin: Optional[str] = None
        self.skip_sheet = skip_sheet
        # {(excel_row_number, column_name): '#RRGGBB' или None}
        self.cell_colors: Dict[Tuple[int, str], Optional[str]] = {}
        # {row_idx: {column: [value, color]}}
        self.colored_data: Dict[Any, Dict[str, list]] = {}

        self.load_excel()

    # ------------------------------------------------------------------ #
    #  Кодировки                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def fix_encoding(text: Any) -> Any:
        """
        Исправляет типичные проблемы с кодировкой (cp1252->cp1251).
        Если текст уже корректный — возвращает как есть.
        """
        if not isinstance(text, str):
            return text

        try:
            return text.encode('cp1252', errors='ignore').decode('cp1251', errors='ignore')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    @staticmethod
    def fix_dataframe_encoding(df: pd.DataFrame) -> pd.DataFrame:
        """ Рекурсивно исправляет кодировку во всех строковых значениях DataFrame. """
        df_fixed = df.copy()
        for col in df_fixed.columns:
            if df_fixed[col].dtype == object:
                df_fixed[col] = df_fixed[col].apply(ExcelReader.fix_encoding)
        return df_fixed

    # ------------------------------------------------------------------ #
    #  Общие helpers                                                      #
    # ------------------------------------------------------------------ #

    def _detect_format(self, file_path: str) -> str:
        """Определяет формат файла по расширению или бинарной сигнатуре."""
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".xls":
            return "xls"
        elif ext in (".xlsx", ".xlsm"):
            return "xlsx"
        else:
            with open(file_path, "rb") as f:
                header = f.read(8)
            if header[:8] == b'\xd0\xcf\x11\xE0\xA1\xB1\x1A\xE1':
                return "xls"
            elif header[:4] == b'PK\x03\x04':
                return "xlsx"
            else:
                raise ValueError(f"Неизвестный формат файла: {file_path}")

    def _should_skip_sheet(self, sheet_name: str, sheet_index: int) -> bool:
        """Проверяет, нужно ли пропустить лист по имени или индексу."""
        if self.skip_sheet is None:
            return False

        skip_list = self.skip_sheet if isinstance(self.skip_sheet, list) else [self.skip_sheet]

        for skip_item in skip_list:
            if isinstance(skip_item, int) and sheet_index == skip_item:
                return True
            if isinstance(skip_item, str) and sheet_name == skip_item:
                return True

        return False

    def _clamp_header_row(self, max_rows: int) -> int:
        """
        Ограничивает header_row, чтобы он не выходил за пределы файла.
        Если header_row >= max_rows — сбрасывает в 0.
        """
        if self.header_row >= max_rows:
            print(f"[ExcelReader] WARNING: header_row={self.header_row} превышает количество строк ({max_rows}). "
                  f"Сбрасываем в 0.")
            return 0
        return self.header_row

    @staticmethod
    def _rgb_to_hex(rgb: Any) -> Optional[str]:
        """Преобразует (r, g, b) или 'AARRGGBB' в '#RRGGBB'."""
        if rgb is None:
            return None
        if isinstance(rgb, (tuple, list)) and len(rgb) >= 3:
            return '#%02X%02X%02X' % (rgb[0], rgb[1], rgb[2])
        if isinstance(rgb, str):
            s = rgb.upper()
            if s in ('00000000', 'FFFFFFFF'):
                return None
            return '#' + s[-6:] if len(s) >= 6 else None
        return None

    def _build_colored_dict(self, df: pd.DataFrame,
                            color_map: Dict[Tuple[int, str], Optional[str]]) -> Dict[Any, Dict[str, list]]:
        """
        Собирает итоговый словарь:
        {row_idx: {column: [value, color]}}
        """
        colored: Dict[Any, Dict[str, list]] = {}
        columns = list(df.columns)
        # Excel-номер первой строки данных (строка заголовка = effective_header + 1)
        first_excel_row = self.effective_header + 2

        for i, idx in enumerate(df.index):
            excel_row = first_excel_row + i
            row_data: Dict[str, list] = {}
            for col in columns:
                if str(col).startswith('Unnamed:'):
                    continue
                value = df.at[idx, col]
                color = color_map.get((excel_row, str(col)))
                row_data[col] = [value, color]
            colored[idx] = row_data

        return colored

    # ------------------------------------------------------------------ #
    #  Загрузка                                                           #
    # ------------------------------------------------------------------ #

    def load_excel(
            self
            , file_path: Optional[str] = None
            , sheet_name: Optional[Union[str, int]] = None
            , color_filter_column: Optional[str] = None
            , encoding: Optional[str] = None
            , skip_sheet: Optional[Union[str, int, List[Union[str, int]]]] = None
    ) -> Optional[Dict[Any, Dict[str, list]]]:
        """
        Загружает данные из Excel файла, собирает цвета ячеек
        и возвращает словарь {row_idx: {column: [value, color]}}.
        """
        path = file_path or self.file_path
        sheet = sheet_name if sheet_name is not None else self.sheet_name
        enc = encoding or self.encoding

        if skip_sheet is not None:
            self.skip_sheet = skip_sheet

        file_format = self._detect_format(path)

        try:
            if file_format == "xls":
                data = self._load_xls(path, sheet, enc)
            else:
                data = self._load_xlsx(path, sheet)

            data = self.fix_dataframe_encoding(data)
            self.data = data

            self.colored_data = self._build_colored_dict(data, self.cell_colors)


            return self.colored_data

        except Exception as e:
            print(f"Ошибка при загрузке файла или листа: {e}")
            if file_path is None and sheet_name is None:
                self.data = None
                self.colored_data = {}
            return None



    @staticmethod
    def _xls_cell_rgb(workbook: xlrd.book.Book, cell: xlrd.sheet.Cell) -> Optional[str]:
        """Возвращает hex-цвет заливки ячейки .xls или None."""
        try:
            xf = workbook.xf_list[cell.xf_index]
            color_index = xf.background.pattern_colour_index
            if color_index in (64, 65, 0):  # default / none
                return None
            rgb = workbook.colour_map.get(color_index)
            return ExcelReader._rgb_to_hex(rgb)
        except Exception:
            return None

    def _open_xls(self, path: str, encoding: Optional[str]) -> xlrd.book.Book:
        """Открывает .xls с formatting_info (нужно для цветов), с fallback без него."""
        kwargs = {}
        if encoding:
            kwargs['encoding_override'] = encoding

        try:
            wb = xlrd.open_workbook(path, formatting_info=True, **kwargs)
            return wb
        except Exception as e:
            print(f"[ExcelReader] formatting_info недоступен ({e}), читаем без форматирования")
            return xlrd.open_workbook(path, **kwargs)

    def _load_xls(self, path: str, sheet: Optional[Union[str, int]],
                  encoding: Optional[str]) -> pd.DataFrame:
        """
        Загружает бинарный .xls через xlrd с поддержкой кодировок
        и чтением цветов заливки ячеек.
        """

        workbook = None
        last_error = None

        if encoding:
            try:
                workbook = self._open_xls(path, encoding)
            except Exception as e:
                print(f"[ExcelReader] Кодировка {encoding} не подошла: {e}")
                last_error = e

        if workbook is None:
            for enc in self.ENCODINGS:
                try:
                    workbook = self._open_xls(path, enc)
                    break
                except Exception as e:
                    last_error = e
                    continue

        if workbook is None:
            raise ValueError(f"Не удалось открыть .xls файл. Последняя ошибка: {last_error}")

        available_sheets = workbook.sheet_names()

        if sheet is not None:
            if isinstance(sheet, int):
                sheet_idx = sheet
                self.sheet_origin = available_sheets[sheet]
            else:
                sheet_idx = available_sheets.index(sheet)
                self.sheet_origin = sheet
        else:
            sheet_idx = None
            for idx, s_name in enumerate(available_sheets):
                if not self._should_skip_sheet(s_name, idx):
                    sheet_idx = idx
                    self.sheet_origin = s_name
                    if self.skip_sheet is not None:
                        print(f"[ExcelReader] Пропущены листы: {self.skip_sheet}. ")
                    break

            if sheet_idx is None:
                raise ValueError(f"Все листы исключены (skip_sheet={self.skip_sheet}). Нет доступных листов.")

        ws = workbook.sheet_by_index(sheet_idx)

        self.effective_header = self._clamp_header_row(ws.nrows)

        data = []
        raw_color_map: Dict[Tuple[int, int], Optional[str]] = {}

        for row_idx in range(ws.nrows):
            row_data = []
            for col_idx in range(ws.ncols):
                cell = ws.cell(row_idx, col_idx)
                val = cell.value
                if val == '':
                    val = float('nan')
                row_data.append(val)

                color = self._xls_cell_rgb(workbook, cell)
                if color:
                    raw_color_map[(row_idx, col_idx)] = color
            data.append(row_data)

        if self.effective_header < len(data):
            headers = data[self.effective_header]
            for i, h in enumerate(headers):
                if pd.isna(h) or str(h).strip() == '':
                    headers[i] = f'Unnamed: {i}'
            df_data = data[self.effective_header + 1:]
            df = pd.DataFrame(df_data, columns=headers)
        else:
            headers = [str(i) for i in range(ws.ncols)]
            df = pd.DataFrame(data)

        # Переиндексируем цвета из (row, col_idx) в (row, column_name)
        self.cell_colors = {}
        for (r, c), rgb in raw_color_map.items():
            col_name = headers[c] if c < len(headers) else f'col_{c}'
            self.cell_colors[(r, str(col_name))] = rgb

        df = self.fix_dataframe_encoding(df)

        if self.track_sheet_origin:
            df['__sheet_origin__'] = self.sheet_origin

        return df



    def _load_xlsx(self, path: str, sheet: Optional[Union[str, int]]) -> pd.DataFrame:
        """Загружает .xlsx через openpyxl/pandas с сбором цветов ячеек."""

        try:
            wb_check = openpyxl.load_workbook(path, data_only=True)
            if sheet is None:
                ws_check = wb_check.active
            elif isinstance(sheet, int):
                ws_check = wb_check.worksheets[sheet]
            else:
                ws_check = wb_check[sheet]
            max_rows = ws_check.max_row
            sheet_names = wb_check.sheetnames
            wb_check.close()
        except Exception:
            max_rows = 999999
            sheet_names = []

        self.effective_header = (self._clamp_header_row(max_rows)
                                 if max_rows < 999999 else self.header_row)

        try:
            raw_data = pd.read_excel(path, sheet_name=sheet, header=self.effective_header)
        except ValueError as e:
            if "Passed header=" in str(e) and "but only" in str(e):
                print(f"[ExcelReader] WARNING: {e}. Пробуем с header=0.")
                self.effective_header = 0
                raw_data = pd.read_excel(path, sheet_name=sheet, header=0)
            else:
                raise

        if isinstance(raw_data, dict):
            if self.skip_sheet is not None:
                skip_list = self.skip_sheet if isinstance(self.skip_sheet, list) else [self.skip_sheet]
                filtered_sheets = {}
                for s_name, s_df in raw_data.items():
                    s_idx = sheet_names.index(s_name) if s_name in sheet_names else -1
                    if s_name not in skip_list and s_idx not in skip_list:
                        filtered_sheets[s_name] = s_df
                raw_data = filtered_sheets

            sheet_names_avail = list(raw_data.keys())
            if sheet_names_avail:
                first_sheet = sheet_names_avail[0]
                df = raw_data[first_sheet]
                sheet_for_colors = first_sheet
            else:
                raise ValueError("Файл Excel не содержит листов (все исключены).")
        else:
            df = raw_data
            sheet_for_colors = sheet

        df = self.fix_dataframe_encoding(df)

        wb = openpyxl.load_workbook(path, data_only=True)

        if sheet_for_colors is None:
            ws = wb.active
            self.sheet_origin = ws.title
        elif isinstance(sheet_for_colors, int):
            ws = wb.worksheets[sheet_for_colors]
            self.sheet_origin = ws.title
        else:
            ws = wb[sheet_for_colors]
            self.sheet_origin = sheet_for_colors

        excel_header_row = self.effective_header + 1

        self.cell_colors = {}
        columns = [str(c) for c in df.columns]

        for row_idx in range(excel_header_row + 1, ws.max_row + 1):
            for col_idx in range(1, min(ws.max_column + 1, len(columns) + 1)):
                cell = ws.cell(row=row_idx, column=col_idx)

                color = None
                if cell.fill and cell.fill.fgColor:
                    color = self._rgb_to_hex(cell.fill.fgColor.rgb)

                if color:
                    col_name = columns[col_idx - 1]
                    self.cell_colors[(row_idx, col_name)] = color

        wb.close()

        if self.track_sheet_origin:
            df['__sheet_origin__'] = self.sheet_origin

        return df



    def get_colored_data(self) -> Dict[Any, Dict[str, list]]:
        """
        Возвращает словарь вида:
        {
            row_idx: {
                name_column: [cell_value, cell_color],
            },
        }
        """
        return self.colored_data

    def get_dict_all_data(self) -> Dict[int, Dict[str, Any]]:
        """Возвращает весь словарь данных из self.data."""
        if self.data is None:
            print("Данные не загружены.")
            return {}
        return {index: row.to_dict() for index, row in self.data.iterrows()}

    def get_headers(self) -> List[str]:
        """Возвращает список заголовков колонок."""
        if self.data is None:
            return []
        return list(self.data.columns)

    def filter_and_save_columns(self, columns_to_save: Union[str, List[str], tuple]):
        """Сохраняет значения из указанных столбцов в словарь."""
        if self.data is None:
            print("Данные не загружены.")
            return

        if isinstance(columns_to_save, str):
            columns_to_save = [columns_to_save]
        elif not isinstance(columns_to_save, list):
            columns_to_save = list(columns_to_save)

        self.columns_save = columns_to_save
        self.filtered_data = {}

        for index, row in self.data.iterrows():
            self.filtered_data[index] = {
                col: row[col] for col in columns_to_save if col in row
            }

    def get_filtered_data(self) -> Optional[Dict[int, Dict[str, Any]]]:
        """Возвращает отфильтрованные данные."""
        return self.filtered_data

    @staticmethod
    def is_empty(val: Any) -> bool:
        """Проверяет, является ли значение пустым."""
        return (val is None or
                (isinstance(val, str) and val.strip().lower() in ("", "nan", "n/a", "none", "-", "null")) or
                (hasattr(pd, 'isna') and pd.isna(val)))

    def get_column_values(self, get_column: str,
                          foc_mode: bool = False,
                          skip_condition: Optional[callable] = None) -> List[str]:
        """Извлекает уникальные значения из указанной колонки."""
        if get_column not in self.columns_save:
            print(f"Название столбцов не совпадают.\n{get_column} в {self.columns_save}")
            return []

        result = []
        all_data_dict = self.get_dict_all_data() if foc_mode else None

        for key in self.filtered_data:
            if foc_mode and skip_condition is not None:
                row_data = all_data_dict.get(key, {})
                if skip_condition(row_data):
                    continue

            value = self.filtered_data[key].get(get_column)
            if value is None or self.is_empty(value):
                continue

            value_str = str(value).strip()
            if not value_str:
                continue

            items = value_str.replace(", ", "|").split("|")

            for item in items:
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
        """Возвращает загруженные данные (DataFrame)."""
        return self.data