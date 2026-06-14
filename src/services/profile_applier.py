"""سرویس اعمال پروفایل - خواندن از دیتابیس و اعمال روی اکانت‌ها"""
import asyncio
import io
import random
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING

from telethon import TelegramClient, errors, functions
from telethon.sessions import StringSession

from src.config import Config
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.database.models import Database

logger = setup_logger(__name__)

# تعداد عکس‌هایی که روی اکانت آپلود می‌شه (رندوم بین این دو عدد)
MIN_PHOTOS_TO_UPLOAD = 3
MAX_PHOTOS_TO_UPLOAD = 7


class ProfileApplier:
    """اعمال پروفایل‌های لیچ شده (از دیتابیس) روی اکانت‌ها"""

    def __init__(self):
        self.api_id = Config.API_ID
        self.api_hash = Config.API_HASH

    async def _load_client(self, session_path: str) -> Optional[TelegramClient]:
        """بارگذاری کلاینت از فایل سشن."""
        try:
            session_string = Path(session_path).read_text(encoding='utf-8')
            client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash,
                proxy=Config.get_proxy_config()
            )
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return None
            return client
        except Exception as e:
            logger.error(f"خطا در بارگذاری سشن: {e}")
            return None

    def _make_username_candidates(self, profile: Dict) -> List[str]:
        """
        ساخت لیست کاندیداهای یوزرنیم طبیعی (بدون _ و پسوند مصنوعی).
        اولویت: یوزرنیم اصلی پروفایل + ترکیب‌های طبیعی از نام.
        """
        base = (profile.get('username') or '').replace('@', '').lower().strip()
        first = (profile.get('first_name') or '').lower().replace(' ', '')
        last  = (profile.get('last_name')  or '').lower().replace(' ', '')

        candidates = []

        if base:
            candidates.append(f"{base}{random.randint(10, 99)}")
            candidates.append(f"{base}{random.randint(1990, 2004)}")
            if last:
                candidates.append(f"{base}{last[0]}{random.randint(1, 9)}")
            candidates.append(f"{base}{random.randint(100, 999)}")

        if first and last:
            candidates.append(f"{first}{last[:5]}")
            candidates.append(f"{first}{last[:3]}{random.randint(1, 99)}")
            candidates.append(f"{first[0]}{last}{random.randint(10, 99)}")

        if first:
            candidates.append(f"{first}{random.randint(10, 99)}")
            candidates.append(f"{first}{random.randint(1990, 2004)}")

        # پاک‌سازی: فقط حرف/عدد/underscore، طول ۵ تا ۳۲
        result = []
        seen = set()
        for c in candidates:
            clean = ''.join(ch for ch in c if ch.isalnum() or ch == '_')
            if len(clean) < 5:
                clean = clean + str(random.randint(100, 999))
            clean = clean[:32]
            if clean not in seen and len(clean) >= 5:
                seen.add(clean)
                result.append(clean)

        return result

    async def _get_account_info(self, client: TelegramClient) -> Dict:
        """دریافت اطلاعات فعلی اکانت (آیدی، شماره، نام فعلی)."""
        try:
            me = await client.get_me()
            return {
                'user_id': me.id,
                'phone': me.phone or '',
                'first_name': me.first_name or '',
                'last_name': me.last_name or '',
                'username': me.username or '',
            }
        except Exception:
            return {}

    async def apply_profile(
        self,
        session_path: str,
        profile: Dict,
        photos: List[bytes],
        apply_photo: bool = True,
        apply_bio: bool = True,
        apply_username: bool = False,
    ) -> Dict:
        """
        اعمال یک پروفایل روی یک اکانت.

        - نام و نام خانوادگی همیشه اعمال می‌شود
        - عکس: رندوم بین MIN_PHOTOS_TO_UPLOAD تا MAX_PHOTOS_TO_UPLOAD عکس آپلود می‌شود
        - بیو: اگر apply_bio=True و پروفایل بیو داشته باشد
        - یوزرنیم: کاندیداهای طبیعی یکی یکی امتحان می‌شوند

        Returns:
            dict: success, account_info (اطلاعات اکانت خودمان), results, message
        """
        client = None
        try:
            client = await self._load_client(session_path)
            if not client:
                return {'success': False, 'message': 'سشن نامعتبر است', 'account_info': {}}

            # اطلاعات اکانت خودمان قبل از تغییر
            account_info = await self._get_account_info(client)

            results = {'name': False, 'bio': False, 'username': False, 'photo': False,
                       'photos_uploaded': 0}

            # ── نام ──────────────────────────────────────────────
            first_name = profile.get('first_name') or 'User'
            last_name  = profile.get('last_name')  or ''
            try:
                await client(functions.account.UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name,
                ))
                results['name'] = True
                logger.info(f"نام اعمال شد: {first_name} {last_name}")
            except errors.FloodWaitError as e:
                logger.warning(f"FloodWait نام: {e.seconds}s")
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                logger.error(f"خطا در اعمال نام: {e}")

            # ── بیو ──────────────────────────────────────────────
            if apply_bio and profile.get('bio'):
                try:
                    await client(functions.account.UpdateProfileRequest(
                        about=profile['bio'][:70]
                    ))
                    results['bio'] = True
                    logger.info("بیو اعمال شد")
                except errors.FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    logger.error(f"خطا در اعمال بیو: {e}")

            # ── یوزرنیم ──────────────────────────────────────────
            if apply_username:
                candidates = self._make_username_candidates(profile)
                set_ok = False
                for candidate in candidates:
                    try:
                        await client(functions.account.UpdateUsernameRequest(username=candidate))
                        results['username'] = True
                        logger.info(f"یوزرنیم اعمال شد: @{candidate}")
                        set_ok = True
                        break
                    except errors.UsernameOccupiedError:
                        logger.warning(f"یوزرنیم @{candidate} گرفته شده، بعدی...")
                        continue
                    except errors.FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                        break
                    except Exception as e:
                        logger.error(f"خطا در اعمال یوزرنیم: {e}")
                        break
                if not set_ok:
                    logger.warning("هیچ کاندیدایی برای یوزرنیم موفق نشد")

            # ── عکس پروفایل (پاک کردن قدیمی + آپلود چند عکس جدید) ──
            if apply_photo and photos:
                # اول همه عکس‌های قبلی رو پاک کن
                try:
                    old_photos = await client(functions.photos.GetUserPhotosRequest(
                        user_id=await client.get_me(),
                        offset=0,
                        max_id=0,
                        limit=100
                    ))
                    if old_photos.photos:
                        await client(functions.photos.DeletePhotosRequest(
                            id=old_photos.photos
                        ))
                        logger.info(f"{len(old_photos.photos)} عکس قدیمی پاک شد")
                except Exception as e:
                    logger.warning(f"خطا در پاک کردن عکس‌های قدیمی: {e}")

                # تعداد رندوم بین MIN و MAX (یا هر چقدر داریم)
                count = random.randint(
                    min(MIN_PHOTOS_TO_UPLOAD, len(photos)),
                    min(MAX_PHOTOS_TO_UPLOAD, len(photos))
                )
                selected_photos = random.sample(photos, count)
                uploaded = 0
                for photo_bytes in selected_photos:
                    try:
                        buf = io.BytesIO(photo_bytes)
                        buf.name = 'profile.jpg'
                        up = await client.upload_file(buf)
                        await client(functions.photos.UploadProfilePhotoRequest(file=up))
                        uploaded += 1
                        logger.info(f"عکس {uploaded}/{count} آپلود شد")
                        if uploaded < count:
                            await asyncio.sleep(1.5)
                    except errors.FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as e:
                        logger.error(f"خطا در آپلود عکس: {e}")

                if uploaded > 0:
                    results['photo'] = True
                    results['photos_uploaded'] = uploaded

            return {
                'success': True,
                'account_info': account_info,
                'results': results,
                'message': f'{sum(v for k,v in results.items() if k != "photos_uploaded" and v)} مورد اعمال شد',
            }

        except Exception as e:
            logger.exception(f"خطا در اعمال پروفایل: {e}")
            return {'success': False, 'message': str(e), 'account_info': {}}
        finally:
            if client:
                await client.disconnect()

    async def bulk_apply_from_db(
        self,
        session_paths: List[str],
        owner_user_id: int,
        db: 'Database',
        apply_photo: bool = True,
        apply_bio: bool = True,
        apply_username: bool = False,
        progress_callback=None,
        cancel_flag: Optional[Dict] = None,
    ) -> Dict:
        """
        اعمال دسته‌جمعی پروفایل‌ها از دیتابیس روی اکانت‌ها.

        هر اکانت یک پروفایل یونیک می‌گیرد.
        پروفایل بلافاصله بعد از اعمال موفق mark_used می‌شود
        تا در صورت خطا یا اجرای موازی، تکراری نشود.
        """
        total = len(session_paths)
        success_count = 0
        failed_count = 0
        no_profile_count = 0
        details: List[Dict] = []

        # پروفایل‌ها رو یکجا می‌گیریم و ID هاشون رو track می‌کنیم
        profiles = await db.get_unused_profiles(owner_user_id, limit=total + 50)

        if not profiles:
            return {
                'success': False,
                'message': 'هیچ پروفایل استفاده‌نشده‌ای در دیتابیس وجود ندارد',
                'success_count': 0,
                'failed_count': 0,
                'no_profile_count': total,
                'total_accounts': total,
                'details': [],
            }

        # set آیدی پروفایل‌هایی که رزرو شدن — جلوگیری از تکراری
        reserved_profile_ids: set = set()
        profile_queue = list(profiles)  # کپی برای pop کردن

        for acc_idx, session_path in enumerate(session_paths, 1):
            if cancel_flag and cancel_flag.get('cancelled'):
                break

            # پیدا کردن اولین پروفایل رزرو نشده
            profile = None
            for p in profile_queue:
                if p['id'] not in reserved_profile_ids:
                    profile = p
                    reserved_profile_ids.add(p['id'])
                    break

            if profile is None:
                no_profile_count += (total - acc_idx + 1)
                logger.warning("پروفایل‌های استفاده‌نشده تموم شدند")
                break

            if progress_callback:
                await progress_callback(
                    acc_idx, total,
                    f"اکانت {acc_idx}/{total} | موفق: {success_count}"
                )

            # عکس‌های این پروفایل
            photos: List[bytes] = []
            if apply_photo:
                photos = await db.get_profile_photos(profile['id'])

            result = await self.apply_profile(
                session_path=session_path,
                profile=profile,
                photos=photos,
                apply_photo=apply_photo,
                apply_bio=apply_bio,
                apply_username=apply_username,
            )

            # اطلاعات اکانت خودمان (نه پروفایل کپی شده)
            acc_info = result.get('account_info', {})
            acc_phone = acc_info.get('phone') or Path(session_path).stem.split('_')[0]
            acc_id    = acc_info.get('user_id') or '—'
            acc_user  = acc_info.get('username') or '—'

            # نام پروفایلی که اعمال شد
            p_first = profile.get('first_name') or ''
            p_last  = profile.get('last_name')  or ''
            p_name  = f"{p_first} {p_last}".strip() or '—'
            p_user  = profile.get('username') or '—'
            p_bio   = (profile.get('bio') or '')[:30]

            if result['success']:
                success_count += 1
                # بلافاصله mark کن تا تکراری نشه
                await db.mark_profile_used(profile['id'], owner_user_id)

                sub = result.get('results', {})
                applied = []
                if sub.get('name'):     applied.append('نام')
                if sub.get('photo'):
                    n = sub.get('photos_uploaded', 1)
                    applied.append(f'عکس×{n}')
                if sub.get('bio'):      applied.append('بیو')
                if sub.get('username'): applied.append('یوزرنیم')

                details.append({
                    'acc_phone': acc_phone,
                    'acc_id':    str(acc_id),
                    'acc_user':  acc_user,
                    'src_id':    str(profile.get('telegram_user_id') or '—'),
                    'status':    'ok',
                    'new_name':  p_name,
                    'new_user':  p_user,
                    'bio':       p_bio,
                    'applied':   ', '.join(applied),
                })
            else:
                failed_count += 1
                reserved_profile_ids.discard(profile['id'])
                logger.error(f"اکانت {acc_idx} ناموفق: {result['message']}")
                details.append({
                    'acc_phone': acc_phone,
                    'acc_id':    str(acc_id),
                    'acc_user':  acc_user,
                    'src_id':    str(profile.get('telegram_user_id') or '—'),
                    'status':    'fail',
                    'new_name':  p_name,
                    'new_user':  p_user,
                    'bio':       p_bio,
                    'applied':   result.get('message', 'خطا')[:50],
                })

            if acc_idx < total:
                delay = Config.DELAY_BETWEEN_ACTIONS + random.randint(0, Config.DELAY_RANDOM_RANGE)
                await asyncio.sleep(delay)

        return {
            'success': True,
            'total_accounts': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'no_profile_count': no_profile_count,
            'details': details,
            'message': f'{success_count} موفق، {failed_count} ناموفق، {no_profile_count} بدون پروفایل',
        }
