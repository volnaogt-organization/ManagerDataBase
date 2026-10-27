from scr.handler.assets_1010 import Header1010
from scr.handler.assets_2012 import Header2012

class MainLogic:
    def __init__(self):
        self.report_1010 = Header1010()
        self.report_2012 = Header2012()

    def main(self, dse_list:list, user_selected_program:int=None):
        if None in [user_selected_program]: return

        for dse in dse_list:
            if user_selected_program == 1010:self.report_1010.main(name_dse=dse)
            if user_selected_program == 2012:self.report_2012.main(name_dse=dse)

