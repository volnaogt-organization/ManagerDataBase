import os
import time

from datetime import timedelta, datetime

from scr.manager_database import MainLogic
from scr.handler.handlers_excel.handler_reader_excel import DataAcquisition, ReaderExcelColumn

main_menu = True
choice_programm = 0
while True:
    if main_menu:
        line_text_choice_program = 'Выберите отчет который хотите обновить в базе данных:'
        indentation_choice_program = (61 - len(line_text_choice_program) - 2) / 2
        choice_programm = input(f"""╔══════════════════════════════════════════════════════════════╗
{'║':<22} {'Manager DataBase':<40}║
╚══════════════════════════════════════════════════════════════╝
  ┌───────────────────────────────────────────────────────────┐
 ┌┤{'':<{indentation_choice_program}}{line_text_choice_program}{'':<{indentation_choice_program}}│
 │└───────────────────────────────────────────────────────────┘
 ├[1] 1010
 ├[2] 2012
 ├[3] УП по очередям
 ├[4] ДСЕ по СЗ и Извещениям
 ├[365] Загрузка годового отчета
 ├[0] Конец
 └─[Программа №:  """)
        main_menu = False
        if choice_programm == '0':
            print('Нажмите Enter для выхода.')
            break
        if choice_programm in ['1', '1010']: choice_programm = 1010
        elif choice_programm in ['2', '2012']: choice_programm = 2012
        elif choice_programm in ['3']: choice_programm = 3
        elif choice_programm in ['4', 'сз']: choice_programm = 4
        elif choice_programm in ['365', 'годовой отчет', 'годовой отчёт']: choice_programm = 365
        else:
            input('Такой программы нет, ошибка.')
            main_menu = True
            continue


    line_text_choice_input_dse = 'Выберите способ ввода ДСЕ: '
    indentation_choice_input_dse = (61 - len(line_text_choice_input_dse) - 2) / 2

    if not choice_programm in [365, 3, 4]:
        choice_input_dse = input(f"""
  ┌───────────────────────────────────────────────────────────┐
 ┌┤{'':<{indentation_choice_input_dse}}{line_text_choice_input_dse}{'':<{indentation_choice_input_dse}}│
 │└───────────────────────────────────────────────────────────┘
 ├[1] Одно ДСЕ (или несколько через '$')
 ├[2] Прочитать столбец из Excel файла
 ├[0] Назад
 └─[Ввод: """)
        if choice_input_dse == '0':
            main_menu = True
            print('\n')
            continue
        if not choice_input_dse in ['1', '2']: continue
    elif choice_programm in [4]:
        choice_input_dse = '4'
    else:
        choice_input_dse = '3'


    save_input = 1

    if choice_input_dse == '1':
        while True:
            print("  [1i]┐")
            print("     ├ Пример : ЛТИЯ.716713.001$ЛТИЯ.712341.004")
            dse_input = input("     ├ Одно ДСЕ (или несколько через '$'), или 0 для отмены выбора: ")

            if dse_input == '0':
                main_menu = True
                print('\n')
                break
            if '$' in dse_input:
                dse_list = dse_input.split('$')
            else:
                dse_list = [dse_input]
            del dse_input

            for dse in dse_list:
                if dse == '':
                    dse_list.remove(dse)
            del dse

            start_time = time.time()

            if choice_programm in [1010,2012]:
                MainLogic().start_generate_report_database_volna(dse_list=dse_list, user_selected_program=choice_programm, save_input=int(save_input))
            elapsed = time.time() - start_time
            duration = timedelta(seconds=elapsed)
            print(f'     ├[Success] Время выполнения программы: {duration} сек.')
            if input(r'     └ Открыть excel файл? [y/N]:') in ['y', 'Y']: os.startfile(
                os.path.join(os.getcwd(), 'result_manager_database_reports.xlsx'))


    if choice_input_dse == '2':
        while True:
            print(" ┌[2i] Введите путь к файлу, или 0 для отмены выбора: ", end='')
            path_to_excel_file = input()
            if '"' in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace('"', '')
            if "'" in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace("'", '')
            if path_to_excel_file in ['0', 'выход']:
                print(f' └[0] Выход')
                main_menu = True
                break
            print(f' └[2i] Открытие файла: {os.path.basename(path_to_excel_file)}')
            view_file = DataAcquisition(path_to_excel_file)

            list_sheets = view_file.get_list_excel_file()
            print(''' ┌───────────────────────────┐
 │   Выберите лист файла:    │
 └┬──────────────────────────┘''')
            for idx_list in range(len(list_sheets)):
                print(f'  ├─[{idx_list}] {list_sheets[idx_list]}')

            choice_name_sheet = input(' └┬[Ввод: ')
            list_name_headers = view_file.get_headers(name_list=list_sheets[int(choice_name_sheet)])

            for idx_list in range(1, len(list_name_headers) + 1):
                print(f'   ├[{idx_list}] {list_name_headers[idx_list - 1]}')

            choice_column = int(input('   ├[Ввод: '))
            print(list_name_headers[choice_column - 1], end=': ')

            data_excel = ReaderExcelColumn(
                path_to_excel_file=path_to_excel_file
                , name_sheet=list_sheets[int(choice_name_sheet)]
            ).get_data_column([choice_column])

            dse_list = list(dict.fromkeys(data_excel.get(list_name_headers[choice_column - 1])))
            print(len(dse_list))
            start_time = time.time()

            if choice_input_dse in [2012]:
                MainLogic().start_generate_report_database_volna(dse_list=dse_list, user_selected_program=choice_programm, save_input=int(save_input))

            elapsed = time.time() - start_time
            duration = timedelta(seconds=elapsed)
            print(f'   ├[Success] Время выполнения программы: {duration} сек.')
            if input(r'   └ Открыть excel файл? [y/N]:') in ['y', 'Y']: os.startfile(
                os.path.join(os.getcwd(), 'result_manager_database_reports.xlsx'))
            break


    if choice_input_dse == '3':
        while True:

            print(" ┌─[3i] Введите путь к файлу, или 0 для отмены выбора: ", end='')
            path_to_excel_file = input()
            if path_to_excel_file in ['0', 'выход']:
                print(f' └[0] Выход')
                main_menu = True

                break

            if '"' in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace('"', '')
            if "'" in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace("'", '')
            print(f' └┬[3i] Запуск программы: [{choice_programm}]')

            start_time = time.time()

            if choice_programm == 365: MainLogic.start_copy_report(path_to_excel_file=path_to_excel_file, user_selected_program=choice_programm)
            if choice_programm == 3: MainLogic.start_copy_report(path_to_excel_file=path_to_excel_file, user_selected_program=choice_programm)

            elapsed = time.time() - start_time
            duration = timedelta(seconds=elapsed)
            print(f' ├[Success] Время выполнения программы: {duration} сек.')
            if input(r' └ Открыть excel файл? [y/N]:') in ['y','Y']: os.startfile(os.path.join(os.getcwd(), 'result_manager_database_reports.xlsx'))



        continue

    if choice_input_dse == '4':
        while True:
            if '1' in input('''  ┌[4] Источник ссылки:
  ├[1] Указать новую
  ├[0] Оставить текущую
  └┬[Ввод: '''):

                print("   ├─[4i][1] Введите путь к файлу, или 0 для отмены выбора: ", end='')
                path_to_excel_file = input()
                if path_to_excel_file in ['0', 'выход']:
                    print(f'   ├[0] Выход')
                    main_menu = True

                    break
            else:
                path_to_excel_file=r"Y:\Служба Главного инженера\ОГТ\ЧПУ\ДСЕ по СЗ и Извещениям.xlsx"

            if '"' in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace('"', '')
            if "'" in path_to_excel_file: path_to_excel_file = path_to_excel_file.replace("'", '')
            print(f'   └┬[4i] Запуск программы: [{choice_programm}]')

            start_time = time.time()

            if choice_programm == 4: MainLogic().start_semi_automatic_update_report(path_to_excel_file=path_to_excel_file, user_selected_program=choice_programm)

            elapsed = time.time() - start_time
            duration = timedelta(seconds=elapsed)
            print(f'  ├[Success] Время выполнения программы: {duration} сек.')
            if input(r'  └ Открыть excel файл? [y/N]:') in ['y', 'Y']: os.startfile(
                os.path.join(os.getcwd(), 'result_manager_database_reports.xlsx'))


        continue
