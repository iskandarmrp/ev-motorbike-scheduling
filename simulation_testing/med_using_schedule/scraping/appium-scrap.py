import time
import csv
import re
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.interaction import Interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder

options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "emulator-5554"
options.app_package = "com.mcash.volta"
options.app_activity = "com.mcash.volta.MainActivity"
options.automation_name = "UiAutomator2"
options.no_reset = True

try:
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    wait = WebDriverWait(driver, 30) 

    # Klik tombol "Lanjutkan"
    try:
        lanjutkan_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//*[@content-desc='Lanjutkan']"))
        )
        lanjutkan_button.click()
        print("Tombol 'Lanjutkan' berhasil ditekan.")
        time.sleep(3)  # waktu untuk animasi transisi halaman
    except Exception as e:
        print("Gagal menekan tombol 'Lanjutkan':", e)

    # Tunggu halaman "Fill personal data" muncul
    # try:
    #     fill_personal_data_button = wait.until(
    #         EC.element_to_be_clickable((By.XPATH, "//*[@content-desc='Fill personal data']"))
    #     )
    #     fill_personal_data_button.click()
    #     print("Tombol 'Fill personal data' berhasil ditekan.")
    #     time.sleep(3)  # waktu untuk animasi transisi halaman
    # except Exception as e:
    #     print("Gagal memuat halaman 'Fill personal data':", e)

    # Tekan tombol back pertama
    try:
        back_button_1 = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//android.view.View[@clickable='true' and @bounds='[0,144][252,340]']"
            ))
        )
        back_button_1.click()
        print("Tombol back pertama berhasil ditekan.")
        time.sleep(2)
    except Exception as e:
        print("Gagal menekan tombol back pertama:", e)

    # Tekan tombol back kedua
    try:
        back_button_2 = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//android.view.View[@clickable='true' and @bounds='[0,144][252,340]']"
            ))
        )
        back_button_2.click()
        print("Tombol back kedua berhasil ditekan.")
        time.sleep(2)
    except Exception as e:
        print("Gagal menekan tombol back kedua:", e)

    # Klik tombol SGB Location
    try:
        sgb_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='SGB\nLocation']"))
        )
        sgb_button.click()
        print("Tombol 'SGB Location' berhasil ditekan.")
    except Exception as e:
        print("Gagal menekan tombol 'SGB Location':", e)

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//android.view.View[@content-desc and contains(@content-desc, 'Full battery estimated')]")))
        time.sleep(5)
    except Exception as e:
        print(f"Timeout waiting for SPKLU data: {e}")

    sgb_data = set()

    previous_data_count = 0
    max_scroll_attempts = 2000
    scroll_attempt = 0

    visited_names = set()

    while scroll_attempt < max_scroll_attempts:
        try:
            time.sleep(1)
            sgb_elements = driver.find_elements(By.XPATH, "//android.view.View[@content-desc]")
            for element in sgb_elements:
                content_desc = element.get_attribute("content-desc")
                print(content_desc)
                if "Tersedia" in content_desc:
                    sgb_tuple = tuple(content_desc.split('\n')) 
                    print(sgb_tuple)
                    if (len(sgb_tuple) > 1):
                        if sgb_tuple[0] not in visited_names:
                            visited_names.add(sgb_tuple[0])
                            try:
                                try:
                                    xpath = f"//android.view.View[@content-desc[starts-with(., '{sgb_tuple[0]}')]]"
                                    target_element = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.XPATH, xpath))
                                    )
                                    target_element.click()
                                    print(f"Berhasil klik elemen berdasarkan sgb_tuple[0]: {sgb_tuple[0]}")
                                except Exception as e:
                                    print(f"Gagal klik elemen dengan sgb_tuple[0]: {sgb_tuple[0]} -> {e}")

                                time.sleep(2) 

                                try:
                                    print(sgb_tuple[0])
                                    try:
                                        jalan_element = WebDriverWait(driver, 20).until(
                                            EC.presence_of_element_located((
                                                By.XPATH,
                                                "//*[" +
                                                    "contains(translate(@content-desc, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jalan') or " +
                                                    "contains(translate(@content-desc, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'jl') or " +
                                                    "contains(translate(@content-desc, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'kec.') or " +
                                                    "contains(translate(@content-desc, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'gg') or " +
                                                    "contains(translate(@content-desc, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ruko')" +
                                                "]"
                                            ))
                                        )
                                        jalan_desc = jalan_element.get_attribute("content-desc")
                                        print(f"Alamat ditemukan: {jalan_desc}")
                                    except Exception as e:
                                        print("Gagal menemukan alamat yang diawali 'Jl.':", e)

                                    try:
                                        xpath = "//android.widget.ImageView[starts-with(@content-desc, 'Available Battery')]"
                                        target_element = WebDriverWait(driver, 20).until(
                                            EC.element_to_be_clickable((By.XPATH, xpath))
                                        )
                                        target_element.click()
                                        print(f"Berhasil klik elemen Available Battery")
                                    except Exception as e:
                                        print(f"Gagal klik elemen Available Battery -> {e}")

                                    try:
                                        # Tunggu elemen muncul
                                        xpath = "//android.view.View[starts-with(@content-desc, 'Available Battery')]"
                                        battery_element = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.XPATH, xpath))
                                        )
                                        content = battery_element.get_attribute("content-desc")
                                        print("Konten Battery:\n", content)

                                        # Ekstrak angka dari baris "Door Number X"
                                        door_numbers = []
                                        lines = content.split("\n")
                                        for line in lines:
                                            match = re.search(r'Door Number (\d+)', line)
                                            if match:
                                                number = int(match.group(1))
                                                door_numbers.append(number)

                                        if door_numbers:
                                            max_door = max(door_numbers)
                                            print(f"Door Number terbesar adalah: {max_door}")
                                        else:
                                            print("Tidak ditemukan 'Door Number' dalam content-desc.")

                                    except Exception as e:
                                        print("Gagal mengambil konten atau memproses Door Number:", e)

                                    print(jalan_desc)
                                    print(max_door)

                                    snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    sgb_data.add(
                                        (sgb_tuple[0],) +
                                        (jalan_desc,) +
                                        (max_door,) +
                                        (snapshot_time,)
                                    )


                                except Exception as e:
                                    print(f"Gagal menemukan Kotak Pengisian: {e}")


                                driver.back() 
                                time.sleep(2) 

                            except Exception as e:
                                print(f"Gagal menekan SPKLU '{sgb_data}': {e}")

            previous_data_count = len(sgb_data)

            print(sgb_data)

            screen_size = driver.get_window_size()
            start_x, start_y = screen_size["width"] // 3, screen_size["height"] *7// 10
            end_x, end_y = start_x, screen_size["height"]*2// 10


            driver.swipe(start_x, start_y, start_x, end_y,1000)
            time.sleep(3) 

        except Exception as e:
            print(f"Error during scrolling and extraction: {e}")
            break

        scroll_attempt += 1

    try:
        with open("sgb_data.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Nama SGB","Alamat","Jumlah Slot","Timestamp"])  # CSV Header
            writer.writerows(sgb_data) 
    except Exception as e:
        print(f"Failed to save data to CSV: {e}")


finally:
    if 'driver' in locals():
        driver.quit()