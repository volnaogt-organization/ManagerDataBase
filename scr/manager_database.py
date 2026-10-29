import os
import time
import concurrent.futures
from datetime import timedelta, datetime

from scr.handler.handlers_db.assets_1010 import Header1010
from scr.handler.handlers_db.assets_2012 import Header2012


class MainLogic:
    def __init__(self):
        # Экземпляры здесь создавать больше не обязательно,
        # так как мы будем создавать их изолированно в каждом потоке.
        pass

    def _process_single_dse(self, dse, dse_index, total_dse, user_selected_program):
        """
        Изолированная функция-воркер.
        Она создает СВОЙ собственный экземпляр класса отчета,
        чтобы потоки не мешали друг другу.
        """
        row_index_list_dse = f'{dse_index}/{total_dse}'

        # Создаем новый объект для каждого потока, чтобы избежать Race Condition
        if user_selected_program == 1010:
            report_handler = Header1010()
            result = report_handler.main(name_dse=dse, row_index_list_dse=row_index_list_dse)
        elif user_selected_program == 2012:
            report_handler = Header2012()
            result = report_handler.main(name_dse=dse, row_index_list_dse=row_index_list_dse)
        else:
            return None

        return dse, result

    def main(self, dse_list: list, user_selected_program: int = None, save_input=0, max_threads=5):
        if user_selected_program is None or not dse_list:
            return

        save_data = {}
        total_dse = len(dse_list)
        t_start = time.time()

        print(f"Начало обработки {total_dse} элементов в {max_threads} потоков...")

        # Используем ThreadPoolExecutor для параллельного выполнения
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Подготавливаем задачи
            futures = [
                executor.submit(
                    self._process_single_dse,
                    dse,
                    i + 1,  # Индексация с 1 для красивого вывода
                    total_dse,
                    user_selected_program
                )
                for i, dse in enumerate(dse_list)
            ]

            # Собираем результаты по мере их выполнения
            for future in concurrent.futures.as_completed(futures):
                try:
                    dse, result = future.result()
                    if result:
                        # Ключом делаем сам dse, а не его порядковый номер.
                        # Это гарантирует, что данные не перепутаются.
                        save_data[dse] = result
                except Exception as e:
                    print(f"Ошибка при обработке одного из DSE: {e}")

        elapsed = time.time() - t_start
        duration = timedelta(seconds=elapsed)
        print(f'Время обращения к базе данных: {duration}')

        if save_input:
            from scr.excel_assets.enters.excel_enter import ExcelDataInserter

            writer = ExcelDataInserter(file_path=os.path.join(os.getcwd(), 'result.xlsx'))
            writer.insert_data(data=save_data, sheet_name=datetime.now().strftime("%d.%m.%Y"))