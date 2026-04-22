from playwright.sync_api import sync_playwright
import time

def login_and_save_state():
    print("\n[ TIZIMGA TAYYORLASH ] Instagram vizual ochilmoqda...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="en-US"
        )
        page = context.new_page()
        
        page.goto("https://www.instagram.com/accounts/login/")
        
        print("\n=======================================================")
        print("  1. Ochilgan brauzerda Instagram profilingizga kiring!")
        print("  (Agar bloklanishdan qo'rqsangiz Fake akkaunt oching)")
        print("  2. Profilga to'liq kirib, 'Lenta (Uy)' ko'ringuncha kuting.")
        print("  3. Shundan SO'NGGINA PASTDAGI TUGMANI BOSING (ENTER)  ")
        print("=======================================================\n")
        
        input("Tayyor bo'lgach klaviaturadan ENTER ni bosing...")
        
        # Brauzer barcha cookie klitinini saqlab oladi
        context.storage_state(path="state.json")
        print("\n✅ ZO'R! Sessiya 'state.json' deb saqlandi.")
        print("Endi asosiy botimiz doim o'sha akkauntdan foydalanib yashirincha ma'lumot oladi!")
        
        browser.close()

if __name__ == "__main__":
    login_and_save_state()
