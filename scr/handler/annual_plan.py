import pandas as pd
from datetime import datetime

from scr.excel_assets.readers.excel_reader_cell_value import ExcelReader
from scr.database_assets.handling_database.handler_annual_plan import SQLiteDatabaseAnnualPlan


class HandlerAnnualPlan:
    def __init__(self):
        self.reader_data = None
        self.data_color_cell = {}
        self.data = {}

        self.color_flow = '#F2F1D9'
        self.color_segment = '#FFFBF0'

    def read_file(self, path_to_file):
        reader = ExcelReader(
            file_path=path_to_file
            , header_row=13
        )
        reader_data = reader.get_colored_data()
        data = {}
        flow = 'NONE'
        segment = 'NONE'
        for row_idx, row_data in reader_data.items():
            for column_idx, column_data in row_data.items():
                if column_idx == 'Бух заказ':
                    if column_data[1] == self.color_flow:
                        flow = column_data[0]
                        data.update({flow: {}})
                        break
                    elif column_data[1] == self.color_segment:
                        segment = column_data[0]
                        data[flow].update({segment: {}})
                        break
                if not row_idx in data[flow][segment].keys():
                    data[flow][segment].update({row_idx: {}})
                data[flow][segment][row_idx].update({column_idx: column_data[0]})

        self.data = data.copy()
        del data

    def save_database(self):
        database_anual_plan = SQLiteDatabaseAnnualPlan()
        database_anual_plan.delete_all()

        date = datetime.now().strftime("%d.%m.%Y")

        for Flow, Flow_data in self.data.items():
            for Segment, Segment_data in Flow_data.items():
                for AccountingOrder, AccountingOrder_data in Segment_data.items():
                    nomenclature = str(AccountingOrder_data.get('Номенклатура') or '').split(' ', maxsplit=1)
                    if pd.isna(AccountingOrder_data.get('Номенклатура', None)): continue
                    print(AccountingOrder_data.get('Номенклатура', None))

                    dse, shortname = nomenclature[0], nomenclature[1] if len(nomenclature) > 1 else ''

                    database_anual_plan.set_program_db(
                        Flow=Flow
                        , Segment=Segment
                        , AccountingOrder=AccountingOrder
                        , ProductionPlan=AccountingOrder_data.get('План производства', None)
                        , Nomenclature=AccountingOrder_data.get('Номенклатура', None)
                        , ClientContract=AccountingOrder_data.get('Заказчик по договору', None)
                        , ContractTerm=AccountingOrder_data.get('Срок по договору', None)
                        , Purpose=AccountingOrder_data.get('Назначение', None)
                        , FullAccountingOrder=f'{Flow}/{Segment}/{AccountingOrder}'
                        , DateStart=date
                        , DrawNoStr=dse
                        , ShortName=shortname
                    )

    def main(self, path_to_file):
        self.read_file(path_to_file=path_to_file)
        self.save_database()
        return self.data


if __name__ == '__main__':
    app = HandlerAnnualPlan()
    app.main(
        path_to_file=r"C:\Users\yakovlev_nd\Documents\тест план года.xlsx"
    )
# app = ExcelReader(
#     file_path=r"C:\Users\yakovlev_nd\Documents\тест план года.xlsx"
#     , header_row=13
# )
# for idx_row, row in app.get_dict_all_data().items():
#     print(idx_row,row)
