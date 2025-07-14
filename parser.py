# Подключение библиотеки для паралельного выполнения кода
from concurrent.futures import ProcessPoolExecutor

# 👇 Эта функция будет вызываться параллельно (главная функция и еще есть функция main которая ее запускает)


def run_task(args):
    # Аргументы, передаваемые функцие main
    from_city, to_city, mode, dimensions = args
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    import json
    import os
    from concurrent.futures import ProcessPoolExecutor
    import atexit

    RESULTS_FILE = "delivery_results.json"

    # Настройки для открытия браузер
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")

    # Установка и запуск браузера с настройками
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    # Будет ждать 20 сек до появляения элементов на странице
    wait = WebDriverWait(driver, 20)

    def reset_calculator():
        # Открытие через созданный браузер страницы
        driver.get("https://calculator-dostavki.ru/")
        # Ожидание 3 сек чтобы все элементы прогрузились
        time.sleep(3)
        # Для проверки ошибок, а внутрь обработка клика по кнопке куки уведомлений
        try:
            cookie_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.cookie-btn")))
            cookie_btn.click()
        except:
            pass

    # Получает два чекбокса и в зависимости от условия кликает на них
    def set_delivery_mode(mode):
        warehouse = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[name='mode[0]']")))
        door = driver.find_element(By.CSS_SELECTOR, "input[name='mode[3]']")
        if mode == "склад-склад":
            if not warehouse.is_selected():
                warehouse.click()
            if door.is_selected():
                door.click()
        elif mode == "дверь-дверь":
            if not door.is_selected():
                door.click()
            if warehouse.is_selected():
                warehouse.click()

    # Получает id поля вводу и название города
    def fill_city(field_id, city_name):
        # Ждет пока поле станет кликабельным и очищает его чтобы начать ввод
        field = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
        field.clear()
        # Делит строку на символы
        for char in city_name:
            # Вводит по одному символу в поле
            field.send_keys(char)
            # Задержка перед вводом символа
            time.sleep(0.1)
        # Задержка после ввода чтобы появился список с варианта
        time.sleep(2)
        # Нажатие клавиши вниз чтобы подтвердить вариант
        field.send_keys(Keys.ARROW_DOWN)
        # Короткая пауза для подтверждения выбора
        time.sleep(0.5)
        # Ввод enter в поле
        field.send_keys(Keys.ENTER)

    # Получает название полей и ищет их, а потом вбивает туда значение
    def fill_dimensions(dimensions):
        for name, value in dimensions.items():
            field = wait.until(EC.element_to_be_clickable((By.NAME, name)))
            field.clear()
            field.send_keys(str(value))

    # Функция для получения результатов
    def get_results():
        # Ждет загрузки таблицы результатов (метод presence...проверяет наличие элемента)
        # wait - который был создан в самом верху и здесь его метод который ждет пока выполнится условие
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".scroll-table table")))
        time.sleep(2)
        # Ищутся все строки таблицы
        rows = driver.find_elements(
            By.CSS_SELECTOR, ".scroll-table table tbody tr")
        results = []
        # Перебираются все строки
        for row in rows:
            # Ищутся элементы тд
            cells = row.find_elements(By.TAG_NAME, "td")
            # 3 таких ячейки дожны найтись
            if len(cells) == 3:
                # Если в них записно это, их надо пропустить
                if "цена" in cells[0].text.lower() or "компания" in cells[2].text.lower():
                    continue
                # Получает из таблицы данные и записывает в массив
                try:
                    price = cells[0].text.strip()
                    delivery = ' '.join(cells[1].text.strip().split())
                    try:
                        company_img = cells[2].find_element(By.TAG_NAME, "img")
                        company = company_img.get_attribute("alt").strip()
                    except:
                        company = cells[2].text.strip().split("\n")[0]
                    try:
                        tariff = cells[2].find_element(
                            By.CLASS_NAME, "mdl").text.strip()
                    except:
                        tariff = ""
                    results.append({
                        "company": company,
                        "tariff": tariff,
                        "price": price,
                        "delivery": delivery
                    })
                except:
                    continue
        # Возвразает массив с данными
        return results
    # Запись результата в файл

    # def append_result_to_file(result):
    #     lockfile = "delivery_results.lock"
    #     while os.path.exists(lockfile):
    #         time.sleep(0.1)
    #     open(lockfile, "w").close()
    #     # Проверяет есть ли файл json и читает данные из него, а если его нет, создает пустой json
    #     if os.path.exists(RESULTS_FILE):
    #         with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    #             try:
    #                 data = json.load(f)
    #             except:
    #                 data = []
    #     else:
    #         data = []
    #     # Добавление прочитанных результатов в data
    #     data.append(result)
    #     # Добавление их в файл
    #     with open(RESULTS_FILE, "w", encoding="utf-8") as f:
    #         json.dump(data, f, ensure_ascii=False, indent=2)
    #     # Закрытие локфайла
    #     os.remove(lockfile)
    def append_result_to_file(result):
        lockfile = "delivery_results.lock"
        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            try:
                # Попытка создания lock-файла
                with open(lockfile, 'x') as f:
                    # Записываем PID для идентификации
                    f.write(str(os.getpid()))

                try:
                    # Чтение существующих данных
                    if os.path.exists(RESULTS_FILE):
                        try:
                            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except (json.JSONDecodeError, IOError) as e:
                            print(f"⚠ Ошибка чтения файла: {e}")
                            data = []
                    else:
                        data = []

                    # Добавление новых данных
                    data.append(result)

                    # Запись с временным файлом
                    temp_file = RESULTS_FILE + ".tmp"
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    # Атомарная замена файла
                    os.replace(temp_file, RESULTS_FILE)

                    return True  # Успешная запись

                finally:
                    # Гарантированное удаление lock-файла
                    if os.path.exists(lockfile):
                        os.remove(lockfile)

            except FileExistsError:
                # Ожидание освобождения блокировки
                time.sleep(0.5 * (attempt + 1))
                attempt += 1
                print(
                    f"⌛ Ожидание lock-файла (попытка {attempt}/{max_attempts})")

            except Exception as e:
                print(f"❌ Критическая ошибка: {e}")
                if os.path.exists(lockfile):
                    try:
                        os.remove(lockfile)
                    except:
                        pass
                return False

        print("⚠ Превышено максимальное количество попыток")
        return False

    # def append_result_to_file(result):
    #     lockfile = "delivery_results.lock"
    # try:
    #     # Ожидание освобождения lock-файла + удаление зависших
    #     while os.path.exists(lockfile):
    #         if time.time() - os.path.getmtime(lockfile) > 300:  # 5 минут
    #             os.remove(lockfile)
    #         time.sleep(0.1)

    #     # Создание lock-файла с PID
    #     with open(lockfile, "w") as f:
    #         f.write(str(os.getpid()))

    #     # Удаление lock-файла при завершении программы
    #     atexit.register(lambda: os.remove(lockfile)
    #                     if os.path.exists(lockfile) else None)

    #     # Чтение и запись данных
    #     if os.path.exists(RESULTS_FILE):
    #         try:
    #             with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    #                 data = json.load(f)
    #         except (json.JSONDecodeError, IOError):
    #             data = []
    #     else:
    #         data = []

    #     data.append(result)

    #     with open(RESULTS_FILE, "w", encoding="utf-8") as f:
    #         json.dump(data, f, ensure_ascii=False, indent=2)

    # finally:
    #     # Удаление lock-файла при выходе из функции
    #     if os.path.exists(lockfile):
    #         os.remove(lockfile)
    # def append_result_to_file(result):
    #     lockfile = "delivery_results.lock"
    #     try:
    #         # Ожидание освобождения lock-файла + удаление зависших
    #         while os.path.exists(lockfile):
    #             if time.time() - os.path.getmtime(lockfile) > 300:  # 5 минут
    #                 os.remove(lockfile)
    #         time.sleep(0.1)

    #         # Создание lock-файла с PID
    #         with open(lockfile, "w") as f:
    #             f.write(str(os.getpid()))

    #         # Удаление lock-файла при завершении программы
    #         atexit.register(lambda: os.remove(lockfile)
    #                         if os.path.exists(lockfile) else None)

    #         # Чтение и запись данных
    #         if os.path.exists(RESULTS_FILE):
    #             try:
    #                 with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    #                     data = json.load(f)
    #             except (json.JSONDecodeError, IOError):
    #                 data = []
    #         else:
    #             data = []

    #         data.append(result)

    #         with open(RESULTS_FILE, "w", encoding="utf-8") as f:
    #             json.dump(data, f, ensure_ascii=False, indent=2)

    #     finally:
    #         # Удаление lock-файла при выходе из функции
    #         if os.path.exists(lockfile):
    #             os.remove(lockfile)

    # Основной скрипт функции run task
    # key = (from_city, to_city, mode)
    # Вывод информации в консоль
    print(f"➡ {from_city} → {to_city} | {mode}")
    try:
        # Скрывает куки кнопкой
        reset_calculator()
        # Вызывает функциюдля чекбоксов
        set_delivery_mode(mode)
        # Вбивают название городов и габариты
        fill_city("city1", from_city)
        fill_city("city2", to_city)
        fill_dimensions({
            "weight[]": dimensions[0],
            "length[]": dimensions[1],
            "width[]": dimensions[2],
            "height[]": dimensions[3],
        })
        # Нажимает на кнопку отправки
        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit']")))
        submit_btn.click()
        print(f"⌛ {from_city} → {to_city} | Ожидаем результаты...")
        time.sleep(5)
        # Запуск функции для получения результатов
        results = get_results()
        if results:
            for res in results:
                full = {
                    "from": from_city,
                    "to": to_city,
                    "mode": mode,
                    "weight": dimensions[0],
                    "length": dimensions[1],
                    "width": dimensions[2],
                    "height": dimensions[3],
                    **res
                }
                # Вызов функции для записи результатов в файл
                append_result_to_file(full)
                print(
                    f"✅ {res['company']} | {res['tariff']} — {res['price']} руб")
        else:
            print(f"⚠ Нет результатов для {from_city} → {to_city}")
            no_res = {
                "from": from_city,
                "to": to_city,
                "mode": mode,
                "weight": dimensions[0],
                "length": dimensions[1],
                "width": dimensions[2],
                "height": dimensions[3],
                "status": "no_results"
            }
            append_result_to_file(no_res)
    except Exception as e:
        print(f"❌ Ошибка в {from_city} → {to_city} | {e}")
    # Закрытие браузера
    finally:
        driver.quit()


def main():
    cities = ["Алматы",
              "Апатиты",
              "Алдан",
              "Анадырь",
              "Анапа",
              "Астана",
              "Астрахань",
              "Барнаул",
              "Бахчисарай",
              "Биробиджан",
              "Благовещенск",
              "Братск",
              "Буденновск",
              "Буйнакск",
              "Владивосток",
              "Владикавказ",
              "Волжский",
              "Волгоград",
              "Воронеж",
              "Грозный",
              "Донецк",
              "Дзержинский",
              "Екатеринбург",
              "Избербаш",
              "Иваново",
              "Ижевск",
              "Иркутск",
              "Казань",
              "Карабулак",
              "Калининград",
              "Караганда",
              "Каспийск",
              "Кемерово",
              "Киров",
              "Когалым",
              "Комсомольск-на-Амуре",
              "Кострома",
              "Краснодар",
              "Красноярск",
              "Курган",
              "Курск",
              "Кызыл",
              "Липецк",
              "Луганск",
              "Магадан",
              "Магнитогорск",
              "Маджалис",
              "Майкоп",
              "Мариуполь",
              "Мирный",
              "Москва",
              "Мурманск",
              "Набережные Челны",
              "Надым",
              "Назрань",
              "Нальчик",
              "Находка",
              "Невинномысск",
              "Нефтекамск",
              "Нефтеюганск",
              "Нижневартовск",
              "Нижнекамск",
              "Нижний Бестях",
              "Нижний Новгород",
              "Нижний Тагил",
              "Новокузнецк",
              "Новороссийск",
              "Новосибирск",
              "Новый Уренгой",
              "Омск",
              "Оренбург",
              "Орёл",
              "Орск",
              "Пенза",
              "Пермь",
              "Петрозаводск",
              "Петропавловск-Камчатский",
              "Пятигорск",
              "Ростов-на-Дону",
              "Самара",
              "Санкт-Петербург",
              "Саранск",
              "Саратов",
              "Саки",
              "Северодвинск",
              "Севастополь",
              "Симферополь",
              "Смоленск",
              "Сочи",
              "Ставрополь",
              "Стерлитамак",
              "Сургут",
              "Сыктывкар",
              "Тамбов",
              "Томск",
              "Тольятти",
              "Тюмень",
              "Улан-Удэ",
              "Ульяновск",
              "Уссурийск",
              "Уссуна",
              "Уфа",
              "Ухта",
              "Хабаровск",
              "Ханты-Мансийск",
              "Хасавюрт",
              "Чебоксары",
              "Челябинск",
              "Череповец",
              "Черкесск",
              "Чита",
              "Шахты",
              "Шымкент",
              "Якутск",
              "Ялта",
              "Ярославль",
              "Зеленоград",
              "Домодедово",
              "Подольск",
              "Балашиха",
              "Королев",
              "Одинцово",
              "Реутов",
              "Люберцы",
              "Красногорск",
              "Мытищи",
              "Жуковский",
              "Долгопрудный",
              "Электросталь",
              "Железногорск",
              "Гатчина",
              "Тосно",
              "Всеволожск",
              "Лабытнанги",
              "Советский",
              "Снежинск",
              "Озерск",
              "Славянск-на-Кубани",
              "Ейск",
              "Геленджик",
              ]
    sizes = [
        (10, 10, 10, 10),
        (25, 25, 25, 25),
        (50, 50, 50, 50),
        (75, 75, 75, 75),
    ]
    delivery_modes = ["склад-склад", "дверь-дверь"]

    tasks = []
    seen_pairs = set()

    # Подготовка пар городов и габаритов и передача в функцию run_task
    for city1 in cities:
        for city2 in cities:
            pair_key = tuple(sorted([city1, city2]))  # без направления
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            for mode in delivery_modes:
                for size in sizes:
                    tasks.append((city1, city2, mode, size))

    # 🚀 Параллельный запуск задач
    with ProcessPoolExecutor(max_workers=4) as executor:
        executor.map(run_task, tasks)


if __name__ == "__main__":
    main()
