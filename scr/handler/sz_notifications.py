from time import strftime

import pandas as pd
from datetime import datetime

from scr.database_assets.handling_database.handler_sz_notifications import SQLiteDatabaseSzNotifications
from scr.excel_assets.readers.excel_fast_reader_row import ExcelReader


class HandlerSzNotifications:
    def __init__(self):
        self.reader_data = None

    def read_file(self, path_to_file):
        reader = ExcelReader(
            file_path=path_to_file
            , sheet_name='Лист1'
        )
        self.reader_data = reader.get_dict_all_data()

    def save_database(self):
        db = SQLiteDatabaseSzNotifications()
        db.delete_all()

        date = datetime.now().strftime("%d.%m.%Y")

        def fmt(v):
            return v.strftime("%d.%m.%Y") if hasattr(v, "strftime") else str(v)[:10]

        batch = []
        for row_data in self.reader_data.values():
            row_data = {k: (None if pd.isna(v) else v) for k, v in row_data.items()}
            pdraw = row_data.get('Изделие')
            draw = row_data.get('ДСЕ')
            date_letter = fmt(row_data.get('Дата пиьсма'))

            batch.append(
            {
                'DateLetter': date_letter,
                'InformationLetter': row_data.get('Инф из письма'),
                'PDrawNoStr': pdraw,
                'PShortName': row_data.get('Наименование'),
                'DrawNoStr': draw,
                'ShortName': row_data.get('Наименование2'),
                'Signed': fmt(row_data.get('Подписано')),
                'WorkCenter': row_data.get('РЦ'),
                'Completed': fmt(row_data.get('Выполнено')),
                'WorkCenterAccordingTechnicalPlan': row_data.get('РЦ по ТП'),
                'Comments': row_data.get('Комментарии'),
                'Closed': row_data.get('Закрыто'),
                'AutoCommentParameter': row_data.get('Авто коммент. (параметр автоматизации)'),
                'Terrorist': row_data.get('Технолог'),
                'DateStart': date,
                'DateLetterPDrawNoStrDrawNoStr': f'{date_letter}/{pdraw}/{draw}/{len(batch)}',
            }
        )

        db.replace_all_notifications(batch)

    def main(self, path_to_file):
        self.read_file(path_to_file)
        self.save_database()


if __name__ == '__main__':
    app = HandlerSzNotifications()
    app.main(path_to_file=r"C:\Users\yakovlev_nd\Desktop\Tests\ManagerDataBase\ДСЕ по СЗ и Извещениям.xlsx")
