from datetime import datetime

from scr.database_assets.handling_database.handler_queue_management import SQLiteDatabaseQueueManagement
from  scr.excel_assets.readers.excel_reader_row import ExcelReader


class HandlerQueueManagement:
    def __init__(self):
        self.reader_data = None

    def read_file(self, path_to_file):
        reader = ExcelReader(
            file_path=path_to_file
            , header_row=5
        )
        self.reader_data = reader.get_dict_all_data()

    def save_database(self):
        database_queue_management = SQLiteDatabaseQueueManagement()
        database_queue_management.delete_all()

        date = datetime.now().strftime("%d.%m.%Y")

        for idx_row, row_data in self.reader_data.items():
            nomenclature = row_data.get('Полное наименование',None)
            ci = row_data.get('IC',None)

            database_queue_management.set_program_db(
                Very=row_data.get('Оч',None)
                ,Launch=row_data.get('Запуск',None)
                ,Issue=row_data.get('Выпуск',None)
                ,IC=ci
                ,Nomenclature=nomenclature
                ,DrawNoStr=row_data.get('Артикул',None)
                ,ShortName=row_data.get('Наименование',None)
                ,WorkCenter_11102=row_data.get('11102',None)
                ,WorkCenter_11401=row_data.get('11401',None)
                ,WorkCenter_11402=row_data.get('11402',None)
                ,WorkCenter_11403=row_data.get('11403',None)
                ,WorkCenter_11404=row_data.get('11404',None)
                ,DateStart=date
                ,IcNomenclature=f'{ci}/{nomenclature}'
            )

    def main(self, path_to_file):
        self.read_file(path_to_file)
        self.save_database()





if __name__ == '__main__':
    app = HandlerQueueManagement()
    app.main(path_to_file=r"C:\Users\yakovlev_nd\Desktop\Tests\ManagerDataBase\УП по очередям.xlsx")