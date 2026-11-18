from scr.excel_assets.readers.excel_reader_column import ExcelColumnReader


class DataAcquisition:
    def __init__(self, path_to_excel_file):
        self.reader_excel_file = ExcelColumnReader(file_path=path_to_excel_file)

    def get_list_excel_file(self) -> list:
        return self.reader_excel_file.sheet_names

    def get_headers(self, name_list) -> list:
        self.reader_excel_file.select_sheet(name_list)
        return self.reader_excel_file.headers


class ReaderExcelColumn:
    def __init__(self, path_to_excel_file:str, name_sheet:str):
        self.reader_excel_file = ExcelColumnReader(
            file_path=path_to_excel_file
            , sheet=name_sheet
        )

    def get_data_column(self, names_columns: list) -> dict[str, list]:
        result_data = self.reader_excel_file.get_columns(columns=names_columns)

        for name_column in names_columns:
            data_column = result_data.get(name_column, [])

            result_data[name_column] = [item for item in data_column if item is not None]

        return result_data


if __name__=='__main__':
    app = DataAcquisition(
        path_to_excel_file=r"C:\Users\yakovlev_nd\Desktop\ДСЕ по СЗ и Извещениям.xlsx"
    )
    print(app.get_list_excel_file())
    print(app.get_headers(name_list='Лист1'))

    #
    app2 = ReaderExcelColumn(
        path_to_excel_file=r"C:\Users\yakovlev_nd\Desktop\ДСЕ по СЗ и Извещениям.xlsx"
        , name_sheet='Лист1'
    )
    print(app2.get_data_column(names_columns=['ДСЕ']))
