from scr.handler.handlers_db.assets_1010 import Header1010
from scr.handler.handlers_db.assets_2012 import Header2012

class MainLogic:
    def __init__(self):
        self.report_1010 = Header1010()
        self.report_2012 = Header2012()

    def main(self, dse_list:list, user_selected_program:int=None,save_input=0):
        if None in [user_selected_program]: return

        save_data = {}
        for dse in dse_list:
            if user_selected_program == 1010:save_data[len(save_data)] = self.report_1010.main(name_dse=dse)
            if user_selected_program == 2012:save_data[len(save_data)] = self.report_2012.main(name_dse=dse)
        if save_input:
            from scr.excel_assets.enters.excel_enter import ExcelDataInserter
            writer = ExcelDataInserter(file_path=os.path.join(os.getcwd(), 'result.xlsx'))
            writer.insert_data(data={'': save_data}, sheet_name=date)

