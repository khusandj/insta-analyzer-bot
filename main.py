import os
import json
import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from pydantic import BaseModel

app = FastAPI(title="SMM Instagram Ai Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yangi API klyuch o'rnatildi
GEMINI_API_KEY = "AIzaSyDesbdtatg21Blx4VxG1HqzURfLaCU2e-0" 
genai.configure(api_key=GEMINI_API_KEY)

# Keshlash (server xotirasida saqlanadi, har bir tugma uchun qayta instagramga kirmaydi)
scraped_cache = {}

def extract_top_posts(username: str):
    # Agar bu foydalanuvchini yaqinda ushlagan bo'lsak, xotiradan beramiz
    if username in scraped_cache:
        return scraped_cache[username]
        
    intercepted_posts = []

    def handle_response(response):
        if "api/v1/users/web_profile_info/" in response.url or "graphql/query" in response.url:
            try:
                data = response.json()
                if 'data' in data and 'user' in data['data']:
                    user_info = data['data']['user']
                    nodes = user_info['edge_owner_to_timeline_media']['edges']
                    for node in nodes:
                        p = node['node']
                        post_data = {
                            "id": p.get("id"),
                            "type": p.get("__typename"),
                            "comments_count": p.get("edge_media_to_comment", {}).get("count", 0),
                            "likes_count": p.get("edge_media_preview_like", {}).get("count", 0),
                            "views_count": p.get("video_view_count", 0),
                            "caption": p.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "") if p.get("edge_media_to_caption", {}).get("edges") else "",
                            "url": f"https://www.instagram.com/p/{p.get('shortcode')}/"
                        }
                        intercepted_posts.append(post_data)
            except Exception:
                pass

    try:
        with Stealth().use_sync(sync_playwright()) as p:
            # Server (Render) da ishlayotganida oyna (GUI) bo'lmasligi shart, shuning uchun True qilinadi!
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            
            if os.path.exists("state.json"):
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="en-US",
                    storage_state="state.json"
                )
            else:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="en-US"
                )
            
            page = context.new_page()
            page.on("response", handle_response)
            
            page.goto(f"https://www.instagram.com/{username}/", timeout=60000)
            
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                time.sleep(2)
                
            browser.close()
    except Exception as e:
        print("Playwright xatosi:", e)
        return []

    unique_posts_dict = {p['id']: p for p in intercepted_posts if p.get('id')}
    unique_posts = list(unique_posts_dict.values())
    
    for post in unique_posts:
        post['score'] = post.get('likes_count', 0) + (post.get('views_count', 0) * 0.5)
        
    top_posts = sorted(unique_posts, key=lambda x: x.get('score', 0), reverse=True)[:5]
    
    # Xotiraga yozib qolish (bot shu malumotlarni botta eslab qolib har xil senariylarda ishlatadi)
    scraped_cache[username] = top_posts
    return top_posts

def generate_ai_response(top_posts, task_type):
    base_context = f"""
Senga foydalanuvchi qiziqayotgan Instagram profili (raqobatchisi yoki o'rganilishi kerak bo'lgan sahifa)ning eng muvaffaqiyatli (top 5 ta eng ko'p qamrov olgan) postlari JSON formatida yuborilmoqda. Ularni chuqur tahlil qilib xotiranga ol:
{json.dumps(top_posts, ensure_ascii=False)}

Mijoz nima so'rasa AYNAN SHU MA'LUMOTLARGA (yutuqlarga, videolarning izohlariga va turiga) tayangan holda gapirishing shart.
Endi quyidagi aniq vazifani o'zbek tilida professional, toza va minimalist markdown formatida yozib ber:

"""
    
    instructions = {
        "smm": "SMM TAHLIL MUTEAXASSISI SIFATIDA: Bu postlar nima uchun bunchalik viral bo'lgan? Raqobatchida qanday trend, format (Reels/Karusel) ustunligi borligini tahlil qil. Kopirayting uslubi va hashtaglarni qanday ishlatilishiga xulosa ber.",
        "content_plan": "KONTENT REJA TUZUVCHI SIFATIDA: Yuqoridagi mana shu eng yaxshi ishlagan postlarning ustun g'oyalarini modellashtirgan holda, mening mijozim akkaunti uchun qanday videolar yozishimiz kerakligi bo'yicha yorqin, aniq, 7 kunlik amaliy Kontent Reja tayyorlab ber (qaysi kuni qanaqa mavzu, nima format tavsiya qilinadi?).",
        "script": "SENARIY YOZUVCHI SIFATIDA: Yuqoridagi Top postlar xotirasidan eng ko'p e'tibor tortgan, eng viral bo'lib ketishi aniq bo'lgan 1 ta mavzuni generatsiya qil ustunroq g'oya o'ylab top, va 30 soniyali yangi Reels uchun detallarga boy Senariy tuzib ber (Qanday Hook bilan boshlanadi? Ekranda nima ko'rinadi vizual ravishda? Va kadrda orqada qanday gapiriladi matn?).",
        "audience": "AUDITORIYA TAHLILI MUTAXASSISI SIFATIDA: Shunday yuqori qamrov olgan mana shu postlarga qanday odamlar jalb bo'lishgan, ularning Auditoriya portretini tasvirlab ber. Ularning psixologiyasini o'rgan (Nimani xohlashadi asosan? Eng katta og'riqlari (Pain pointlari) nima ekanligini taxmin qil va nima uchun shu sahifaga yopishishmoqda?).",
        "reels": "REELS VIDEO METRIKA MUTAXASSISI SIFATIDA: Bu yerdagi videolarni view (ko'rishlar soni) metrikalarini va kommentariy qoldirishganini hisobga olib, nega baribir video formati katta natija keltirayotganini tahlil qil. Eng kuchli video qanday algoritm evaziga urib ketgani borasida tushuntirish va o'z maslahatlaringni ber."
    }

    prompt = base_context + instructions.get(task_type, instructions["smm"])
    
    try:
        model = genai.GenerativeModel('gemini-3.1-pro-preview')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI xatoligi ro'y berdi: {str(e)}"


# === API YO'NALISHLARI ===

@app.get("/api/scrape")
def api_scrape(username: str):
    """Faqatgina Playwright yordamida botni ishga solib ma'lumot qirqib olish (Cached)"""
    if not username:
        raise HTTPException(status_code=400, detail="Username kiritilmadi!")
        
    top_posts = extract_top_posts(username)
    
    if not top_posts:
        return {"status": "error", "message": "Instagram bu profilni bloklab qo'ydi yoki ma'lumot topilmadi yoxud shartli limit."}
        
    return {"status": "success", "username": username, "scraped_count": len(top_posts)}


@app.get("/api/generate")
def api_generate(username: str, task: str):
    """Scrape qilib olingan xotira asosida AI'ga har xil senariy va rejalarni tuzdirish"""
    # Keshdan oladi (ikkinchi marta brauzer ochilmaydi)
    top_posts = extract_top_posts(username)
    
    if not top_posts:
         return {"status": "error", "message": "Avval izlash tugmasini bosib profil ma'lumotlarini qirqib olish shart."}
         
    ai_text = generate_ai_response(top_posts, task)
    
    return {"status": "success", "ai_analysis": ai_text}

# Statik sayt ulanishi
app.mount("/", StaticFiles(directory="static", html=True), name="static")
