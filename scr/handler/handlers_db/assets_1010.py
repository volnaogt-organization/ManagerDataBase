import os

import pyodbc
import pandas as pd

from datetime import datetime

from scr.database_assets.handling_database.handler_report_1010 import SQLiteDatabaseReport1010


class Header1010:
    def __init__(self):
        self.database_reort2012 = SQLiteDatabaseReport1010()

        self.server = 'DC-HV-SQLVOLNA'
        self.report_2012 = 'SAP_RT'

        self.bool_search_results = 1
        self.row_index_list_dse = ''
        self.list_data_from_database = []

    def script_invocation(self, name_dse):
        available_drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]

        if not available_drivers:
            raise RuntimeError(
                "В системе не найдено ни одного ODBC драйвера для SQL Server! Установите Microsoft ODBC Driver.")

        chosen_driver = available_drivers[0]

        current_date = datetime.now().strftime("%d.%m.%Y")

        conn_str = f'DRIVER={{{chosen_driver}}};SERVER={self.server};DATABASE={self.report_2012};Trusted_Connection=yes;'
        sql_query = f"SET NOCOUNT ON; EXEC _Rep_UpperMatnr2 '{name_dse}', '{current_date}'"


        try:
            with pyodbc.connect(conn_str) as conn:
                try:
                    df = pd.read_sql(sql_query, conn)
                except:pass

            data_list = df.to_dict(orient='records')
            print(f"{name_dse} [{self.row_index_list_dse}]: получено строк: {len(data_list)}")

            if len(data_list) == 0:
                data_list.append({
                    'Matnr': None
                    , 'DrawNoStr': None
                    , 'ShortName': None
                    , 'FinishedGoodsName': None
                    , 'SumAmount': None
                })
                self.bool_search_results = 0

        except Exception as e:
            print(f"Ошибка при выполнении: {e}")
            return

        self.list_data_from_database = data_list.copy()

    def save_report_in_database(self, name_dse: str = None):
        if name_dse is None:
            return

        date = datetime.now().strftime("%d.%m.%Y")

        # 1. Удаляем старые записи (вызываем метод обертки)
        self.database_reort2012.delete_by_name_import(name_dse)

        # 2. Записываем новые данные
        data_save={}
        for row_data in self.list_data_from_database:
            # Исправлены кавычки в f-string, чтобы не было синтаксической ошибки
            in_out_pt = f"{name_dse}/{row_data.get('DrawNoStr', '')}"

            self.database_reort2012.set_program_db(
                NameImport=name_dse,
                DateStart=date,
                InOutPt=in_out_pt,
                SearchResults=self.bool_search_results,
                **row_data
            )

            data_save[len(data_save)] = {
                'NameImport':name_dse
                ,'SearchResults':self.bool_search_results
            }
        return data_save


    def main(self, name_dse,row_index_list_dse=''):
        self.row_index_list_dse=row_index_list_dse
        self.bool_search_results = 1
        if name_dse is None: return {}
        self.script_invocation(name_dse=name_dse)
        return self.save_report_in_database(name_dse=name_dse)


if __name__ == "__main__":
    app = Header1010()
    app.main('ЛТИЯ46451100400000000')
