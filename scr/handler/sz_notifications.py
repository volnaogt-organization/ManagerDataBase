import pandas as pd
from datetime import datetime

from scr.database_assets.handling_database.handler_sz_notifications import SQLiteDatabaseSzNotifications
from scr.excel_assets.readers.excel_reader_row import ExcelReader


class HandlerSzNotifications:
    def __init__(self):
        self.reader_data = None

    def read_file(self, path_to_file):
        reader = ExcelReader(
            file_path=path_to_file
        )
        self.reader_data = reader.get_dict_all_data()

    def save_database(self):
        database_queue_management = SQLiteDatabaseSzNotifications()
        database_queue_management.delete_all()

        date = datetime.now().strftime("%d.%m.%Y")

        for idx_row, row_data in self.reader_data.items():
            row_data = {k: (None if pd.isna(v) else v) for k, v in row_data.items()}
            pdraw_no_str = row_data.get('Изделие', None)
            draw_no_str = row_data.get('ДСЕ', None)

            raw_date = row_data.get('Дата пиьсма', None)
            date_letter = raw_date.strftime("%d.%m.%Y") if hasattr(raw_date, 'strftime') else raw_date
            # date_letter=row_data.get('Дата пиьсма', None).strftime("%d.%m.%Y")

            completed = row_data.get('Выполнено', None)
            completed = completed.strftime("%d.%m.%Y") if hasattr(completed, 'strftime') else completed

            signed =  row_data.get('Подписано', None)
            signed =  signed.strftime("%d.%m.%Y") if hasattr(signed, 'strftime') else signed

            database_queue_management.set_program_db(
                DateLetter=date_letter
                , InformationLetter=row_data.get('Инф из письма', None)
                , PDrawNoStr=pdraw_no_str
                , PShortName=row_data.get('Наименование', None)
                , DrawNoStr=draw_no_str
                , ShortName=row_data.get('Наименование2', None)
                , Signed=signed
                , WorkCenter=row_data.get('РЦ', None)
                , Completed=completed
                , WorkCenterAccordingTechnicalPlan=row_data.get('РЦ по ТП', None)
                , Comments=row_data.get('Комментарии', None)
                , Closed=row_data.get('Закрыто', None)
                , AutoCommentParameter=row_data.get('Авто коммент. (параметр автоматизации)', None)
                , Terrorist=row_data.get('Технолог', None)
                , DateStart=date
                , DateLetterPDrawNoStrDrawNoStr=f'{str(date_letter)}/{pdraw_no_str}/{draw_no_str}'
            )

    def main(self, path_to_file):
        self.read_file(path_to_file)
        self.save_database()


if __name__ == '__main__':
    app = HandlerSzNotifications()
    app.main(path_to_file=r"C:\Users\yakovlev_nd\Desktop\Tests\ManagerDataBase\ДСЕ по СЗ и Извещениям.xlsx")
