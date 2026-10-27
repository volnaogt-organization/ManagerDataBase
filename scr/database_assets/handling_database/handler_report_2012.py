import os
from typing import Dict, Any, List

from scr.database_assets.receiver_sqlite_database import SQLiteManager

REPORT_2012_SCHEMA = {
    'NameImport':'TEXT',
    'TeamNo': 'TEXT',
    'Matnr': 'TEXT',
    'DrawNoStr': 'TEXT',
    'ShortName': 'TEXT',
    'ProductProg': 'TEXT',
    'ProductDoc': 'TEXT',
    'PriorityNo': 'INTEGER',
    'Type': 'TEXT',
    'Matnr1': 'TEXT',
    'NameOper': 'TEXT',
    'NumOper': 'INTEGER',
    'IdProg': 'INTEGER',
    'PDrawNoStr': 'TEXT',
    'PShortName': 'TEXT',
    'DateStart':'TEXT',
    'A11402': 'TEXT',
    'A11403': 'TEXT',
    'A11102': 'TEXT',
    'A11404': 'TEXT',
    'A11402T': 'TEXT',
    'A11403T': 'TEXT',
    'A11102T': 'TEXT',
    'A11404T': 'TEXT',
    'SearchResults':'INTEGER',
    'InOutPt':'TEXT'
}

REPORT_2012_COLUMNS = list(REPORT_2012_SCHEMA.keys())


class SQLiteDatabaseReport2012:
    def __init__(self, db_path: str = r"\\volna.dmn\data\obmen\Служба Главного инженера\ОГТ\ЧПУ\Программы Python\database_program\report_table.db"):
        """
        Инициализация менеджера для отчета 2012.
        :param db_path: Путь к файлу базы данных.
        """
        self.name_dict = 'report_2012'

        self.data_base = SQLiteManager(
            db_path=db_path,
            table_name=self.name_dict,
            schema=REPORT_2012_SCHEMA,
            unique_keys=['InOutPt'],
            indexes=['TeamNo', 'Matnr', 'InOutPt']
        )

    def get_all_db_program(self) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
        """
        Возвращает данные в формате вложенного словаря.
        Структура: TeamNo -> Matnr -> DrawNoStr -> данные_строки.
        """
        rows = self.data_base.get_all()
        result = {}

        for row in rows:
            team_no = row['TeamNo']
            matnr = row['Matnr']
            draw_no = row['DrawNoStr']

            result.setdefault(team_no, {}).setdefault(matnr, {})[draw_no] = row

        return result

    def get_program_data(self, draw_no_str: str) -> List[Dict[str, Any]]:
        """Получить данные по конкретному DrawNoStr."""
        return self.data_base.get_by_field('DrawNoStr', draw_no_str)

    def set_program_db(self, **kwargs):
        """
        Записывает или обновляет данные.
        Использует kwargs для чистоты кода при большом количестве аргументов.
        """
        data = {col: kwargs.get(col, '') for col in REPORT_2012_COLUMNS}

        existing = self.data_base.get_by_field('DrawNoStr', data['DrawNoStr'])

        if existing:
            old = existing[0]
            for col in REPORT_2012_COLUMNS:
                if not data[col]:
                    data[col] = old[col]

        self.data_base.upsert(data)

    def delete_by_name_import(self, name_import: str):
        """Удаляет все записи с указанным NameImport."""
        query = f"DELETE FROM {self.data_base.table_name} WHERE NameImport = ?"
        self.data_base.execute_query(query, (name_import,))

    def __del__(self):
        """Безопасное закрытие соединения при удалении объекта."""
        if hasattr(self, 'data_base') and self.data_base:
            self.data_base.close()


if __name__ == "__main__":
    # Путь к БД (директория создастся автоматически)
    db_file = r"\\volna.dmn\data\obmen\Служба Главного инженера\ОГТ\ЧПУ\Программы Python\database_program\report_table.db"
    app = SQLiteDatabaseReport2012(db_path=db_file)

    # Пример записи данных
    app.set_program_db(
        NameImport='002',
        TeamNo='11102',
        Matnr='ЛТИЯ73521405500000000',
        DrawNoStr='ЛТИЯ.735214.055',
        ShortName='Площадка',
        ProductProg='LTIY.735214.055 U1.nc; 05.04.2026',
        PriorityNo=0,
        Type='Деталь',
        Matnr1='ЛТИЯ73521405500000000',
        NameOper='Фрезерная с ЧПУ',
        NumOper=4,
        IdProg=5358365,
        PDrawNoStr='ЛТИЯ.464511.004',
        PShortName='Радиостанция «Ширина», индекс Р-225 (изделие Р-225-В ЛТИЯ.464511.004 ЛТИЯ.464511.004 ТУ)'
    )

    # Пример получения данных
    print("Все данные:", app.get_all_db_program())
    print("\nДанные по DrawNoStr:", app.get_program_data('ЛТИЯ.735214.055'))