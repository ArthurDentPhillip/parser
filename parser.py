from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import json
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


RESULTS_FILE = "delivery_results.json"
LOCK_FILE = "delivery_results.lock"
PROGRESS_FILE = "progress.state"


def append_result_to_file(result):
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            with open(LOCK_FILE, 'x') as f:
                f.write(str(os.getpid()))
            try:
                if os.path.exists(RESULTS_FILE):
                    try:
                        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = []
                else:
                    data = []
                data.append(result)
                temp_file = RESULTS_FILE + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, RESULTS_FILE)
                return True
            finally:
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
        except FileExistsError:
            time.sleep(0.5 * (attempt + 1))
            attempt += 1
        except Exception as e:
            print(f"❌ Ошибка при записи: {e}")
            if os.path.exists(LOCK_FILE):
                try:
                    os.remove(LOCK_FILE)
                except:
                    pass
            return False
    print("⚠ Превышено максимальное количество попыток записи")
    return False


def run_task(args):
    from_city, to_city, mode, dimensions, task_index = args
    print(f"➡ {from_city} → {to_city} | {mode}")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    def reset_calculator():
        driver.get("https://calculator-dostavki.ru/")
        time.sleep(3)
        try:
            cookie_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.cookie-btn")))
            cookie_btn.click()
        except:
            pass

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

    def fill_city(field_id, city_name):
        field = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
        field.clear()
        for char in city_name:
            field.send_keys(char)
            time.sleep(0.1)
        time.sleep(2)
        field.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        field.send_keys(Keys.ENTER)

    def fill_dimensions(dimensions):
        for name, value in dimensions.items():
            field = wait.until(EC.element_to_be_clickable((By.NAME, name)))
            field.clear()
            field.send_keys(str(value))

    def get_results():
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".scroll-table table")))
        time.sleep(2)
        rows = driver.find_elements(
            By.CSS_SELECTOR, ".scroll-table table tbody tr")
        results = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) == 3:
                if "цена" in cells[0].text.lower() or "компания" in cells[2].text.lower():
                    continue
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
        return results

    try:
        reset_calculator()
        set_delivery_mode(mode)
        fill_city("city1", from_city)
        fill_city("city2", to_city)
        fill_dimensions({
            "weight[]": dimensions[0],
            "length[]": dimensions[1],
            "width[]": dimensions[2],
            "height[]": dimensions[3],
        })
        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit']")))
        submit_btn.click()
        print(f"⌛ {from_city} → {to_city} | Ожидаем результаты...")
        time.sleep(5)
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
    finally:
        driver.quit()

    save_progress(task_index)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f).get("last_processed", -1)
    return -1


def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"last_processed": index, "timestamp": str(datetime.now())}, f)


def main():
    # Сокращённый список для примера
    cities = ["Москва", "Санкт-Петербург", "Новосибирск"]
    sizes = [(10, 10, 10, 10), (25, 25, 25, 25)]
    delivery_modes = ["склад-склад", "дверь-дверь"]

    seen_pairs = set()
    cities_pairs = []
    for city1 in cities:
        for city2 in cities:
            pair_key = tuple(sorted([city1, city2]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                cities_pairs.append((city1, city2))

    tasks = []
    for pair_index, (city1, city2) in enumerate(cities_pairs):
        for mode in delivery_modes:
            for size in sizes:
                tasks.append((city1, city2, mode, size, len(tasks)))

    last_index = load_progress()
    tasks = tasks[last_index + 1:]

    with ProcessPoolExecutor(max_workers=4) as executor:
        executor.map(run_task, tasks)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true",
                        help="Продолжить с последней позиции")
    args = parser.parse_args()

    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            json.dump([], f)

    if args.resume:
        print("⚡ Режим продолжения работы")

    main()
