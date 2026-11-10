from scr.excel_assets.readers.excel_reader_row import ExcelReader
app = ExcelReader(
    file_path=r"C:\Users\yakovlev_nd\Documents\тест план года.xlsx"
    , header_row=13
)
for idx_row, row in app.get_dict_all_data().items():
    print(idx_row,row)