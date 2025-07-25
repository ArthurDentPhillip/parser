import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Настройки
FROM_CITIES = {
    "Москва": "mos.php",
    "Владивосток": "vlad.php",
    "Новосибирск": "nov.php",
    "Якутск": "yak.php"
}

PARAMS = [
    {"ves": "1", "obem": "0.1"},
    {"ves": "5", "obem": "0.15"},
    {"ves": "10", "obem": "0.2"},
    {"ves": "15", "obem": "0.3"},
    {"ves": "20", "obem": "0.5"},
    {"ves": "25", "obem": "0.8"},
    {"ves": "50", "obem": "1.0"},
    {"ves": "100", "obem": "1.5"},
    {"ves": "200", "obem": "2.0"},
    {"ves": "500", "obem": "3.0"},
    {"ves": "1000", "obem": "5.0"},
    {"ves": "1500", "obem": "8.0"}
]

RESULTS_FILE = "results.json"
PROGRESS_FILE = "progress.json"  # Файл для отслеживания прогресса

def load_existing_results():
    """Загрузка существующих результатов"""
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_progress():
    """Загрузка прогресса последнего запуска"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(progress):
    """Сохранение прогресса"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def save_results(results):
    """Сохранение результатов"""
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 Результаты сохранены ({len(results)} записей)")

def save_result_incremental(result):
    """Добавление результата в файл по одному"""
    results = load_existing_results()
    results.append(result)
    save_results(results)

def parse_city_data(driver, wait, from_city, to_city, param, page):
    """Парсинг данных для одной пары городов"""
    try:
        print(f"🔄 {from_city} → {to_city} | {param['ves']} кг, {param['obem']} м³")

        # Проверяем наличие элемента выбора города
        select_element = wait.until(EC.presence_of_element_located((By.NAME, "kuda")))
        select = Select(select_element)
        
        # Проверяем, доступен ли город назначения
        available_options = [opt.get_attribute("value") for opt in select.options]
        if to_city not in available_options:
            print(f"⚠️  Город {to_city} отсутствует на странице {from_city}")
            return None

        # Выбираем город назначения
        select.select_by_value(to_city)

        # Вводим параметры
        ves_element = wait.until(EC.presence_of_element_located((By.NAME, "ves")))
        ves_element.clear()
        ves_element.send_keys(param["ves"])
        
        obem_element = driver.find_element(By.NAME, "obem")
        obem_element.clear()
        obem_element.send_keys(param["obem"])

        # Нажимаем кнопку
        if page == "vlad.php":
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.fordirect-param[type='submit']")))
        else:
            submit_button = wait.until(EC.element_to_be_clickable(By.ID, "knopka"))
        
        submit_button.click()

        # Ждём появления результатов
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td[align='center'][width='200'] b.h1")))
        
        # Получаем цену
        price_element = driver.find_element(By.CSS_SELECTOR, "td[align='center'][width='200'] b.h1")
        price = price_element.text.strip()

        # Авианакладная
        awb_elements = driver.find_elements(By.CSS_SELECTOR, "td[align='center'][width='200'] span.copy b")
        awb_price = awb_elements[-1].text.strip() if awb_elements else "—"

        # Срок доставки
        all_td = driver.find_elements(By.CSS_SELECTOR, "td[align='center'][width='200']")
        delivery_days = next((td.text.strip() for td in all_td if "дней" in td.text), "Не найдено")

        # Выводим результаты
        print(f"   💰 Цена: {price} руб.")
        print(f"   ✈️  Авианакладная: {awb_price} руб.")
        print(f"   ⏱ Срок: {delivery_days}\n")

        # Возвращаем результат
        return {
            "timestamp": datetime.now().isoformat(),
            "from": from_city,
            "to": to_city.capitalize(),
            "weight": int(param["ves"]),
            "volume": float(param["obem"]),
            "company": "Аэрогруз",
            "tariff": "Основной тариф",
            "price": price,
            "delivery": delivery_days
        }
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге {from_city} → {to_city}: {str(e)[:100]}...\n")
        return None

def main():
    print("🚀 Запуск парсера Аэрогруз...")
    
    # Загружаем прогресс последнего запуска
    progress = load_progress()
    print(f"📊 Прогресс последнего запуска: {progress}")
    
    # Настройки Chrome
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.binary_location = "/usr/bin/chromium-browser"
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        cities_list = list(FROM_CITIES.items())
        
        for from_index, (from_city, page) in enumerate(cities_list):
            # Пропускаем уже обработанные города из прошлого запуска
            if progress.get("last_city_index", -1) > from_index:
                print(f"⏭️  Пропускаем {from_city} (уже обработан)")
                continue
                
            try:
                url = f"https://www.aerogruz.ru/calc/{page}"
                print(f"\n📍 Обработка города отправления: {from_city}")
                
                driver.get(url)
                wait = WebDriverWait(driver, 20)
                
                # Ждем загрузки страницы
                wait.until(EC.presence_of_element_located((By.NAME, "kuda")))

                # Получаем список доступных городов назначения
                select_element = Select(driver.find_element(By.NAME, "kuda"))
                available_to_cities = [opt.get_attribute("value") for opt in select_element.options]

                # Исключаем город-отправитель
                available_to_cities = [city for city in available_to_cities if city and city != from_city.lower()]
                print(f"🏙️  Доступные города назначения: {len(available_to_cities)} шт.")

                # Обрабатываем города назначения
                for city_index, to_city in enumerate(available_to_cities):
                    # Пропускаем уже обработанные города назначения
                    if (progress.get("last_city_index", -1) == from_index and 
                        progress.get("last_city_dest_index", -1) > city_index):
                        print(f"⏭️  Пропускаем {from_city} → {to_city}")
                        continue
                        
                    for param_index, param in enumerate(PARAMS):
                        # Пропускаем уже обработанные параметры
                        if (progress.get("last_city_index", -1) == from_index and 
                            progress.get("last_city_dest_index", -1) == city_index and
                            progress.get("last_param_index", -1) >= param_index):
                            print(f"⏭️  Пропускаем {from_city} → {to_city} ({param['ves']}кг)")
                            continue
                            
                        try:
                            print(f"\n🔄 Попытка: {from_city} → {to_city}")
                            
                            # Переходим на страницу заново для каждой итерации
                            driver.get(url)
                            wait = WebDriverWait(driver, 20)
                            wait.until(EC.presence_of_element_located((By.NAME, "kuda")))
                            
                            result = parse_city_data(driver, wait, from_city, to_city, param, page)
                            
                            # Сохраняем результат и прогресс
                            if result:
                                save_result_incremental(result)
                                
                            # Сохраняем прогресс
                            current_progress = {
                                "last_city_index": from_index,
                                "last_city_dest_index": city_index,
                                "last_param_index": param_index,
                                "last_update": datetime.now().isoformat()
                            }
                            save_progress(current_progress)
                            
                            time.sleep(3)
                            
                        except Exception as e:
                            print(f"⚠️  Пропущена комбинация {from_city} → {to_city} ({param['ves']}кг): {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"❌ Ошибка при обработке города {from_city}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        
    finally:
        if driver:
            driver.quit()
            
        # Очищаем файл прогресса после успешного завершения
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            
        results = load_existing_results()
        print(f"\n✅ Парсинг завершен. Всего записей: {len(results)}")

if __name__ == "__main__":
    main()
