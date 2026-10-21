from scr.database_assets.receiver_sqlite_database import ReceiverDataBase


class SQLiteDatabaseProgrammData:
    def __init__(self):
        self.name_dict = 'report_2012'
        self.data_base = ReceiverDataBase(name_tabel=self.name_dict)

    def get_all_db_program(self):
        """
        Возвращает данные в формате вложенного словаря.
        Структура адаптирована под новые ключевые поля (TeamNo -> Matnr -> DrawNoStr).
        """
        rows = self.data_base.get_all_rows()
        result = {}
        for row in rows:
            # В качестве ключей группировки выберем логичные уникальные идентификаторы,
            # например: TeamNo (вместо машины), Matnr (вместо директории), DrawNoStr (вместо имени DSE)
            team_no = row['TeamNo']
            matnr = row['Matnr']
            draw_no = row['DrawNoStr']

            result.setdefault(team_no, {}).setdefault(matnr, {})[draw_no] = {
                'DrawNoStr': draw_no,
                'ShortName': row['ShortName'],
                'ProductProg': row['ProductProg'],
                'ProductDoc': row['ProductDoc'],
                'PriorityNo': row['PriorityNo'],
                'Type': row['Type'],
                'Matnr1': row['Matnr1'],
                'NameOper': row['NameOper'],
                'NumOper': row['NumOper'],
                'IdProg': row['IdProg'],
                'PDrawNoStr': row['PDrawNoStr'],
                'PShortName': row['PShortName'],
                'A11402': row['A11402'],
                'A11403': row['A11403'],
                'A11102': row['A11102'],
                'A11404': row['A11404'],
                'A11402T': row['A11402T'],
                'A11403T': row['A11403T'],
                'A11102T': row['A11102T'],
                'A11404T': row['A11404T']
            }
        return result

    def get_program_data(self, draw_no_str):
        """Получить данные по конкретному DrawNoStr."""
        # Метод в ReceiverDataBase должен искать по новой колонке DrawNoStr
        rows = self.data_base.get_rows_by_draw_no(draw_no_str)
        return [dict(row) for row in rows]

    def set_program_db(self, **kwargs):
        """
        Записывает или обновляет данные по всем 22 колонкам.
        Использует kwargs для чистоты кода при большом количестве аргументов.
        """
        # Список всех новых колонок для контроля и подстановки пустых строк по умолчанию
        columns = [
            'TeamNo', 'Matnr', 'DrawNoStr', 'ShortName', 'ProductProg', 'ProductDoc',
            'PriorityNo', 'Type', 'Matnr1', 'NameOper', 'NumOper', 'IdProg',
            'PDrawNoStr', 'PShortName', 'A11402', 'A11403', 'A11102', 'A11404',
            'A11402T', 'A11403T', 'A11102T', 'A11404T'
        ]

        # Заполняем переданные значения, если не передано — ставим пустую строку
        data = {col: kwargs.get(col, '') for col in columns}

        # Проверяем существование записи по ключевому полю (например, DrawNoStr)
        existing = self.data_base.get_rows_by_draw_no(data['DrawNoStr'])
        if existing:
            old = existing[0]
            # Если новое значение поля пустое, сохраняем старое значение из БД
            for col in columns:
                if not data[col]:
                    data[col] = old[col]

        # Передаем обновленный словарь аргументов в метод upsert
        self.data_base.upsert_program_data(**data)

    def __del__(self):
        if hasattr(self, 'data_base'):
            self.data_base.close()


if __name__ == "__main__":
    app = SQLiteDatabaseProgrammData()

    # Пример записи данных с новыми названиями колонок
    app.set_program_db(
        TeamNo='11102',
        Matnr='ЛТИЯ73521405500000000',
        DrawNoStr='ЛТИЯ.735214.055',
        ShortName='Площадка',
        ProductProg='LTIY.735214.055 U1.nc; 05.04.2026',
        PriorityNo=0,
        Type='Деталь',
        Matnr1='ЛТИЯ73521405500000000',
        NameOper='Фрезерная с ЧПУ',
        NumOper=4,
        IdProg=5358365,
        PDrawNoStr='ЛТИЯ.464511.004',
        PShortName='Радиостанция «Ширина», индекс Р-225 (изделие Р-225-В ЛТИЯ.464511.004 ЛТИЯ.464511.004 ТУ)'
    )
