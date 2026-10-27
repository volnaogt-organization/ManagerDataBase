import os
from typing import Dict, Any, List

# Импортируем новый универсальный менеджер
from scr.database_assets.receiver_sqlite_database import SQLiteManager

# Схема таблицы: {название_колонки: SQL_тип}
REPORT_1010_SCHEMA = {
    'NameImport':'TEXT',
    'DateStart': 'TEXT',
    'Matnr': 'TEXT',
    'DrawNoStr': 'TEXT',
    'ShortName': 'TEXT',
    'SumAmount': 'INTEGER',
    'SearchResults':'INTEGER',
    'InOutPt':'TEXT'
}

REPORT_1010_COLUMNS = list(REPORT_1010_SCHEMA.keys())


class SQLiteDatabaseReport1010:
    def __init__(self, db_path: str = r"\\volna.dmn\data\obmen\Служба Главного инженера\ОГТ\ЧПУ\Программы Python\database_program\report_table.db"):
        """
        Инициализация менеджера для отчета 1010.
        :param db_path: Путь к файлу базы данных.
        """
        self.name_dict = 'report_1010'

        self.data_base = SQLiteManager(
            db_path=db_path,
            table_name=self.name_dict,
            schema=REPORT_1010_SCHEMA,
            unique_keys=['InOutPt'],
            indexes=['InOutPt', 'NameImport', 'DrawNoStr']
        )

    def get_all_db_program(self) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
        rows = self.data_base.get_all()
        result = {}

        for row in rows:
            draw_no_str = row['DrawNoStr']
            matnr = row['Matnr']
            name_import = row['NameImport']

            result.setdefault(draw_no_str, {}).setdefault(matnr, {})[name_import] = row

        return result

    def get_program_data(self, draw_no_str: str) -> List[Dict[str, Any]]:
        """Получить данные по конкретному DrawNoStr."""
        return self.data_base.get_by_field('DrawNoStr', draw_no_str)

    def set_program_db(self, **kwargs):

        data = {col: kwargs.get(col, '') for col in REPORT_1010_COLUMNS}

        existing = self.data_base.get_by_field('DrawNoStr', data['DrawNoStr'])

        if existing:
            old = existing[0]
            for col in REPORT_1010_COLUMNS:
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
    db_file = r"\\volna.dmn\data\obmen\Служба Главного инженера\ОГТ\ЧПУ\Программы Python\database_program\report_table.db"
    app = SQLiteDatabaseReport1010(db_path=db_file)
    app.set_program_db(
        NameImport='weqewq'
        ,DateStart='qweqwec'
        ,Matnr='qweqweqw'
        ,DrawNoStr='qweewq'
        ,ShortName='eee'
        ,SumAmount='ui2378gb'
    )


    print("Все данные:", app.get_all_db_program())
    print("\nДанные по DrawNoStr:", app.get_program_data('ЛТИЯ.735214.055'))