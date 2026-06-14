"""اسکریپت برای update کردن کد کشور همه اکانت‌ها"""
import asyncio
from src.database import Database
from src.utils.countries import detect_country_from_phone

async def update_all_countries():
    """update کردن کد کشور برای همه اکانت‌ها"""
    db = Database()
    await db.init_db()
    
    # دریافت همه اکانت‌ها
    accounts = await db.get_accounts()
    
    print(f"📊 تعداد کل اکانت‌ها: {len(accounts)}")
    print("🔄 در حال update کردن کد کشورها...\n")
    
    updated = 0
    for account in accounts:
        if account.phone:
            country_code = detect_country_from_phone(account.phone)
            if country_code != 'UNKNOWN':
                await db.update_account_country(account.phone, country_code)
                print(f"✅ {account.phone} → {country_code}")
                updated += 1
            else:
                print(f"⚠️ {account.phone} → نامشخص")
    
    print(f"\n✅ تکمیل شد! {updated} اکانت update شد.")
    
    # نمایش آمار کشورها
    countries = await db.get_countries()
    if countries:
        print("\n📊 آمار کشورها:")
        for country in countries:
            from src.utils.countries import get_country_name
            print(f"  {get_country_name(country['country_code'])}: {country['count']} اکانت")

if __name__ == "__main__":
    asyncio.run(update_all_countries())
