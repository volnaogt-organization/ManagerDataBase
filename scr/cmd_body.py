import os

from scr.manager_database import MainLogic
from scr.handler.handlers_excel.handler_reader_excel import DataAcquisition, ReaderExcelColumn

main_menu = True
choice_programm = 0
while True:
    if main_menu:
        line_text_choice_program = 'Выберите отчет который хотите обновить в базе данных:'
        indentation_choice_program = (61-len(line_text_choice_program) - 2)/2
        choice_programm = input(f"""╔════════════════════════════════════════════════════════════╗
{'║':<21} {'Manager DataBase':<39}║
╚════════════════════════════════════════════════════════════╝
 ┌───────────────────────────────────────────────────────────┐
┌┤{'':<{indentation_choice_program}}{line_text_choice_program}{'':<{indentation_choice_program}}│
│└───────────────────────────────────────────────────────────┘
├[1] 1010
├[2] 2012
├[0] Конец
└─[Программа №:  """)
        main_menu = False
        if choice_programm == '0':
            print('Нажмите Enter для выхода.')
            break
        if choice_programm in ['1', '1010']:
            choice_programm = 1010
        elif choice_programm in ['2', '2012']:
            choice_programm = 2012
        else:
            input('Такой программы нет, ошибка.')

            break

    line_text_choice_input_dse = 'Выберите способ ввода ДСЕ: '
    indentation_choice_input_dse = (61 - len(line_text_choice_input_dse) - 2) / 2

    choice_input_dse = input(f"""
 ┌───────────────────────────────────────────────────────────┐
┌┤{'':<{indentation_choice_input_dse}}{line_text_choice_input_dse}{'':<{indentation_choice_input_dse}}│
│└───────────────────────────────────────────────────────────┘
├[1] Одно ДСЕ (или несколько через '$'): ЛТИЯ.716713.001$ЛТИЯ.712341.004
├[2] Прочитать столбец из Excel файла
├[0] Назад
└─[Ввод: """)
    if choice_input_dse == '0':
        main_menu = True
        print('\n')
        continue
    if not choice_input_dse in ['1','2']: continue

#     save_input = int(input(''' ┌───────────────────────────────┐
# ┌┤   Сохранить выход в файле?    │
# │└───────────────────────────────┘
# ├[1] Да
# ├[0] Нет
# └─[Ввод:'''))
    save_input = 1

    if choice_input_dse == '1':
        while True:
            dse_input = input("[1] Одно ДСЕ (или несколько через '$'): ")
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

            MainLogic().main(dse_list=dse_list, user_selected_program=choice_programm, save_input=int(save_input))
    if choice_input_dse == '2':
            while True:
                # print(r"┌[2] Введите путь к файлу: C:\Users\yakovlev_nd\Documents\задачи по 1010.xlsx")
                print("┌[2] Введите путь к файлу: ", end='')
                path_to_excel_file = input()
                # path_to_excel_file = r"C:\Users\yakovlev_nd\Documents\задачи по 1010.xlsx"
                print(f'└[2] Открытие файла: {os.path.basename(path_to_excel_file)}')
                view_file= DataAcquisition(path_to_excel_file)

                list_sheets = view_file.get_list_excel_file()
                print('''┌───────────────────────────┐
│   Выберите лист файла:    │
└┬──────────────────────────┘''')
                for idx_list in range(len(list_sheets)):
                    print(f' ├─[{idx_list}] {list_sheets[idx_list]}')

                choice_name_sheet = input(' └┬[Ввод: ')
                list_name_headers = view_file.get_headers(name_list=list_sheets[int(choice_name_sheet)])

                for idx_list in range(1,len(list_name_headers)+1):
                    print(f'  ├─[{idx_list}] {list_name_headers[idx_list-1]}')

                choice_column = int(input('  └─[Ввод: '))
                print(list_name_headers[choice_column-1], end=': ')

                data_excel = ReaderExcelColumn(
                    path_to_excel_file=path_to_excel_file
                    , name_sheet=list_sheets[int(choice_name_sheet)]
                ).get_data_column([choice_column])

                dse_list = list(dict.fromkeys(data_excel.get(list_name_headers[choice_column-1])))
                print(len(dse_list))

                MainLogic().main(dse_list=dse_list, user_selected_program=choice_programm, save_input=int(save_input))
                break
