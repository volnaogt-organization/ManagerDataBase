from scr.manager_database import MainLogic
main_menu = True
choice_programm = 0
while True:
    if main_menu:
        choice_programm = input(f"""╔════════════════════════════════════════════════════════════╗
{'║':<21} {'Manager DataBase':<39}║
╚════════════════════════════════════════════════════════════╝
Выберите отчет который хотите обновить в базе данных:
    1. 1010
    2. 2012
    0. Конец 
Программа №:  """)
        main_menu = False
        if choice_programm == '0':
            print('Нажмите Enter для выхода.')
            break
        if choice_programm in ['1','1010']: choice_programm = 1010
        elif choice_programm in ['2','2012']: choice_programm = 2012
        else:
            input('Такой программы нет, ошибка.')

            break

    dse_input = input('Введите ДСЕ, через "$" или 0 для : ')
    if dse_input == '0':
        main_menu = True
        print('\n')
        continue
    if '$' in dse_input: dse_list = dse_input.split('$')
    else : dse_list = [dse_input]
    del dse_input

    for dse in dse_list:
        if dse == '':
            dse_list.remove(dse)
    del dse

    MainLogic().main(dse_list=dse_list, user_selected_program=choice_programm)


