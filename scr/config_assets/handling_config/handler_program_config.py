import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


from scr.config_assets.receiver_config import ReceiverConfig


class ConfigMainProgram:
    def __init__(self):
        self.data_base = ReceiverConfig()

    def get_all_config_program(self):
        self.data_base.load()
        return self.data_base.data.get('program', '')

    def set_config_progrm(self, key, data):
        if key in self.data_base.data.get('program', '').keys():
            self.data_base.data['program'][key] = data
            self.data_base.save()
            self.data_base.load()

    def get_size_config(self):
        self.data_base.load()
        return self.data_base.data['program'].get('size', '')

    def set_size_config(self, key_name_file, path_to_file):

        data = self.data_base.data['program'].get('size', '')

        if key_name_file in data.keys():
            self.data_base.data['program']["size"][key_name_file] = path_to_file
            self.data_base.save()
            self.data_base.load()
        else:
            print(
                f"Данного ключа('{key_name_file}') нет в словаре 'size', возможные варианты {list(data.keys())}"
            )

if __name__ == "__main__":
    app = ConfigMainProgram()
