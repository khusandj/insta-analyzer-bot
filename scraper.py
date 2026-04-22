from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import json

def scrape_ig_posts(username):
    print("🚀 Playwright brauzeri ishga tushirilmoqda (Interceptor rejimida)...")
    
    # Biz ushlab olingan API ma'lumotlarini shu yerda saqlaymiz
    intercepted_posts = []

    def handle_response(response):
        # Instagram postlar ma'lumotlarini api/v1 lari yoki graphql orqali yuboradi
        # Biz barcha JSONlarni ushlab postlar bor yo'qligini qidiramiz
        if "api/v1/users/web_profile_info/" in response.url or "graphql/query" in response.url:
            try:
                data = response.json()
                # GraphQL yoki Profile info datasi shunday shaklda keladi:
                if 'data' in data and 'user' in data['data']:
                    user_info = data['data']['user']
                    nodes = user_info['edge_owner_to_timeline_media']['edges']
                    for node in nodes:
                        p = node['node']
                        post_data = {
                            "id": p.get("id"),
                            "shortcode": p.get("shortcode"),
                            "type": p.get("__typename"),
                            "comments_count": p.get("edge_media_to_comment", {}).get("count", 0),
                            "likes_count": p.get("edge_media_preview_like", {}).get("count", 0),
                            "views_count": p.get("video_view_count", 0),
                            "caption": p.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "") if p.get("edge_media_to_caption", {}).get("edges") else "",
                            "url": f"https://www.instagram.com/p/{p.get('shortcode')}/"
                        }
                        intercepted_posts.append(post_data)
            except Exception as e:
                pass

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="en-US"
        )
        page = context.new_page()

        # Dasturni tarmoq trafigini ushlab olishga ulaymiz
        page.on("response", handle_response)

        print(f"🔎 Sahifaga kirilmoqda: https://www.instagram.com/{username}/")
        
        # Sahifaga o'tish
        retries = 3
        while retries > 0:
            try:
                page.goto(f"https://www.instagram.com/{username}/", timeout=60000)
                break
            except Exception as e:
                print("Sahifa qayta yuklanmoqda, kutamiz...")
                retries -= 1
        
        print("⏳ Ma'lumotlarni o'zlashtirish uchun yana 8 soniya kutamiz...")
        
        # Dastur pastga scroll qilsa qo'shimcha postlar ham yuklanadi
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(2)
            
        time.sleep(2) 
        
        browser.close()

    # == 2-BOSQICH: MA'LUMOTLARNI SARALASH VA TOP-POSTLARNI TOPISH ==
    
    if len(intercepted_posts) > 0:
        print(f"\nJami {len(intercepted_posts)} ta post API dan ushlab olindi!")
        
        # Ball tizimini kiritamiz: (Likes * 1) + (Views * 0.5) 
        # Eng yuqori ball olgan 3 ta postni ajratamiz
        for post in intercepted_posts:
            post['score'] = post['likes_count'] + (post['views_count'] * 0.5)
            
        top_posts = sorted(intercepted_posts, key=lambda x: x['score'], reverse=True)[:5]
        
        print("\n🏆 == ENG ZO'R (TOP 5) POSTLAR ==\n")
        for i, tp in enumerate(top_posts, 1):
            print(f"#{i} Post URL: {tp['url']}")
            print(f"   Turi: {tp['type']}")
            print(f"   Ko'rishlar (Views): {tp['views_count']}")
            print(f"   Layklar: {tp['likes_count']}")
            print(f"   Kommentariylar: {tp['comments_count']}")
            # Matn (caption) juda uzun bo'lib ketsa, faqat ilk 100 belgisini chiqaramiz
            short_caption = tp['caption'].replace('\n', ' ')[:100] + '...' if len(tp['caption']) > 100 else tp['caption'].replace('\n', ' ')
            print(f"   Matni (Caption): {short_caption}")
            print("-" * 50)
            
        # Ma'lumotlarni keyinchalik AI'ga berish uchun json fayl qilib saqlab qolamiz
        with open(f"{username}_top_posts.json", "w", encoding="utf-8") as file:
            json.dump(top_posts, file, indent=4, ensure_ascii=False)
            
        print(f"\nBarcha top ma'lumotlar {username}_top_posts.json fayliga saqlandi. Endi bu json'ni AI analizga yuborishingiz mumkin.")
            
    else:
        print("\n⚠️ Kechirasiz, API tarmog'idan JSON ma'lumot topilmadi. Instagram bugun himoyasi kuchli bo'lishi mumkin yoki ochiq sahifa ochilmadi.")

if __name__ == "__main__":
    # Sinab ko'ramiz
    target_profile = "cristiano"
    scrape_ig_posts(target_profile)
