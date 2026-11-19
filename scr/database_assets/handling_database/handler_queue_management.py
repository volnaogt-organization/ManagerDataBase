import os
from typing import Dict, Any, List

from scr.database_assets.receiver_sqlite_database import SQLiteManager

Queue_Management_SCHEMA = {
    'Very':'TEXT',
    'Launch': 'TEXT',
    'Issue': 'TEXT',
    'IC': 'TEXT',
    'Nomenclature': 'TEXT',
    'DrawNoStr': 'TEXT',
    'ShortName': 'TEXT',
    'WorkCenter_11102': 'TEXT',
    'WorkCenter_11401': 'TEXT',
    'WorkCenter_11402': 'TEXT',
    'WorkCenter_11403': 'TEXT',
    'WorkCenter_11404': 'TEXT',
    'DateStart':'TEXT',
    'IcNomenclature': 'TEXT',
}

Queue_Management_COLUMNS = list(Queue_Management_SCHEMA.keys())


class SQLiteDatabaseQueueManagement:
    def __init__(self, db_path: str = r"\\volna.dmn\data\obmen\Служба Главного инженера\ОГТ\ЧПУ\Программы Python\database_program\report_table.db"):
        """
        Инициализация менеджера для годового отчета.
        :param db_path: Путь к файлу базы данных.
        """
        self.name_dict = 'queue_management'

        self.data_base = SQLiteManager(
            db_path=db_path,
            table_name=self.name_dict,
            schema=Queue_Management_SCHEMA,
            unique_keys=['IcNomenclature'],
            indexes=['ShortName','WorkCenter_11102', 'WorkCenter_11401','WorkCenter_11402', 'WorkCenter_11403','WorkCenter_11404']
        )

    def get_all_db_program(self) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
        """
        Возвращает данные в формате вложенного словаря.
        Структура: Flow -> Segment -> AccountingOrder -> данные_строки.
        """
        rows = self.data_base.get_all()
        result = {}

        for row in rows:
            team_no = row['IC']
            matnr = row['Nomenclature']
            draw_no = row['ShortName']

            result.setdefault(team_no, {}).setdefault(matnr, {})[draw_no] = row

        return result

    def get_program_data(self, draw_no_str: str) -> List[Dict[str, Any]]:
        """Получить данные по конкретному ShortName."""
        return self.data_base.get_by_field('ShortName', draw_no_str)

    def set_program_db(self, **kwargs):
        """
        Записывает или обновляет данные.
        Использует kwargs для чистоты кода при большом количестве аргументов.
        """
        data = {col: kwargs.get(col, '') for col in Queue_Management_COLUMNS}

        existing = self.data_base.get_by_field('IcNomenclature', data['IcNomenclature'])

        if existing:
            old = existing[0]
            for col in Queue_Management_COLUMNS:
                if not data[col]:
                    data[col] = old[col]

        self.data_base.upsert(data)

    def delete_by_name_import(self, name_import: str):
        """Удаляет все записи с указанным DateStart."""
        query = f"DELETE FROM {self.data_base.table_name} WHERE DateStart = ?"
        self.data_base.execute_query(query, (name_import,))

    def delete_all(self):
        """Удаляет все записи из таблицы."""
        query = f"DELETE FROM {self.data_base.table_name}"
        self.data_base.execute_query(query)

    def __del__(self):
        """Безопасное закрытие соединения при удалении объекта."""
        if hasattr(self, 'data_base') and self.data_base:
            self.data_base.close()
