"""سرویس لیچر - استخراج اعضا از تاریخچه پیام‌های گروه"""
import asyncio
import io
import random
from pathlib import Path
from typing import List, Dict, Optional, Set, TYPE_CHECKING

from telethon import TelegramClient, errors, functions
from telethon.sessions import StringSession
from telethon.tl.types import (
    User, Message, MessageService,
    ChatInviteAlready, ChatInvite,
    PeerUser,
)

from src.config import Config
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.database.models import Database

logger = setup_logger(__name__)

MAX_PHOTOS_PER_PROFILE = 5


class Leecher:
    """لیچر - استخراج اعضا از تاریخچه پیام‌های گروه"""

    def __init__(self):
        self.api_id = Config.API_ID
        self.api_hash = Config.API_HASH

    # ─────────────────────────────────────────────────────────────
    # متدهای کمکی
    # ─────────────────────────────────────────────────────────────

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
            logger.error(f"خطا در بارگذاری سشن {session_path}: {e}")
            return None

    async def _resolve_group(self, client: TelegramClient, group_link: str):
        """پیدا کردن entity گروه از لینک."""
        try:
            link = group_link.strip()

            if '/+' in link or 'joinchat/' in link:
                hash_part = link.split('/')[-1].replace('+', '')
                try:
                    invite_info = await client(
                        functions.messages.CheckChatInviteRequest(hash_part)
                    )
                    if isinstance(invite_info, ChatInviteAlready):
                        return invite_info.chat
                    elif isinstance(invite_info, ChatInvite):
                        result = await client(
                            functions.messages.ImportChatInviteRequest(hash_part)
                        )
                        return result.chats[0]
                except errors.UserAlreadyParticipantError:
                    pass
                except Exception as e:
                    logger.error(f"خطا در resolve لینک خصوصی: {e}")
                    raise

            username = link.split('/')[-1].lstrip('@')
            return await client.get_entity(username)

        except Exception as e:
            logger.error(f"خطا در پیدا کردن گروه '{group_link}': {e}")
            raise

    async def _fetch_user_bio(self, client: TelegramClient, user: User) -> Optional[str]:
        """دریافت بیو کاربر."""
        try:
            full = await client(functions.users.GetFullUserRequest(user))
            return full.full_user.about or None
        except Exception:
            return None

    async def _download_user_photos(
        self, client: TelegramClient, user: User, max_count: int = MAX_PHOTOS_PER_PROFILE
    ) -> List[bytes]:
        """دانلود عکس‌های پروفایل کاربر — فقط در حافظه، بدون ذخیره روی دیسک."""
        photos_bytes: List[bytes] = []
        if not user.photo:
            return photos_bytes
        try:
            photos_result = await client(functions.photos.GetUserPhotosRequest(
                user_id=user,
                offset=0,
                max_id=0,
                limit=max_count
            ))
            for photo in photos_result.photos[:max_count]:
                try:
                    buf = io.BytesIO()
                    await client.download_media(photo, file=buf)
                    buf.seek(0)
                    data = buf.read()
                    if data:
                        photos_bytes.append(data)
                except Exception as e:
                    logger.warning(f"خطا در دانلود عکس user {user.id}: {e}")
        except Exception as e:
            logger.warning(f"خطا در دریافت عکس‌های user {user.id}: {e}")
        return photos_bytes

    def _is_verified(self, user: User) -> bool:
        """بررسی هویت‌دار بودن کاربر (حداقل ۲ از ۳ معیار)."""
        has_photo = user.photo is not None
        has_full_name = bool(user.first_name and user.last_name)
        has_username = user.username is not None
        return sum([has_photo, has_full_name, has_username]) >= 2

    # ─────────────────────────────────────────────────────────────
    # استخراج از تاریخچه پیام‌ها (روش اصلی)
    # ─────────────────────────────────────────────────────────────

    async def get_group_members(
        self,
        session_path: str,
        group_link: str,
        limit: int = 200,
        msg_scan_limit: int = 5000,
        filter_verified: bool = True,
        fetch_bio: bool = True,
        fetch_photos: bool = True,
        owner_user_id: Optional[int] = None,
        db: Optional['Database'] = None,
        seen_ids: Optional[Set[int]] = None,
    ) -> Dict:
        """
        استخراج اعضا از تاریخچه پیام‌های گروه.

        به جای GetParticipants (که تلگرام محدودش کرده)،
        پیام‌های گروه رو اسکن می‌کنه و فرستنده‌های یونیک رو جمع می‌کنه.

        Args:
            session_path: مسیر فایل سشن
            group_link: لینک گروه
            limit: حداکثر تعداد پروفایل برای این اکانت
            msg_scan_limit: حداکثر تعداد پیام برای اسکن
            filter_verified: فقط اعضای هویت‌دار
            fetch_bio: دریافت بیو
            fetch_photos: دانلود عکس‌ها
            owner_user_id: آیدی ادمین (برای چک تکراری در دیتابیس)
            db: نمونه دیتابیس
            seen_ids: set آیدی‌هایی که قبلاً دیده شدن (بین اکانت‌ها share میشه)

        Returns:
            dict: success, message, members, group_title
        """
        client = None
        if seen_ids is None:
            seen_ids = set()

        try:
            client = await self._load_client(session_path)
            if not client:
                return {'success': False, 'message': 'سشن نامعتبر است', 'members': [], 'group_title': ''}

            group_entity = await self._resolve_group(client, group_link)
            group_title = getattr(group_entity, 'title', str(group_link))
            logger.info(f"شروع اسکن تاریخچه '{group_title}' - هدف: {limit} پروفایل")

            # جمع‌آوری user object ها از پیام‌ها
            user_map: Dict[int, User] = {}
            scanned = 0

            async for message in client.iter_messages(group_entity, limit=msg_scan_limit):
                scanned += 1

                if len(user_map) >= limit * 3:
                    # کافیه — بعداً فیلتر می‌کنیم
                    break

                if not isinstance(message, Message):
                    continue

                sender = message.sender
                if not isinstance(sender, User):
                    continue
                if sender.bot or sender.deleted:
                    continue
                if sender.id in user_map:
                    continue

                user_map[sender.id] = sender

                if scanned % 500 == 0:
                    logger.info(f"  اسکن شد: {scanned} پیام | یافت شد: {len(user_map)} کاربر")

            logger.info(f"اسکن تمام شد: {scanned} پیام، {len(user_map)} کاربر یونیک یافت شد")

            # پردازش و فیلتر کاربران
            collected: List[Dict] = []

            for user in user_map.values():
                if len(collected) >= limit:
                    break

                # چک تکراری در seen_ids (بین اکانت‌ها)
                if user.id in seen_ids:
                    continue

                # فیلتر هویت‌دار
                if filter_verified and not self._is_verified(user):
                    continue

                # چک تکراری در دیتابیس
                if db and owner_user_id:
                    if await db.profile_already_leeched(owner_user_id, user.id):
                        seen_ids.add(user.id)
                        continue

                # دریافت بیو
                bio = None
                if fetch_bio:
                    bio = await self._fetch_user_bio(client, user)
                    await asyncio.sleep(0.3)

                # دانلود عکس‌ها (فقط در حافظه)
                photos: List[bytes] = []
                if fetch_photos and user.photo:
                    photos = await self._download_user_photos(client, user)
                    await asyncio.sleep(0.4)

                collected.append({
                    'user_id': user.id,
                    'access_hash': user.access_hash,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'bio': bio,
                    'photos': photos,
                    'has_photo': len(photos) > 0,
                })

                seen_ids.add(user.id)

            logger.info(f"استخراج تمام شد: {len(collected)} پروفایل")
            return {
                'success': True,
                'message': f'{len(collected)} پروفایل استخراج شد',
                'members': collected,
                'group_title': group_title,
                'scanned_messages': scanned,
            }

        except Exception as e:
            logger.exception(f"خطا در استخراج اعضا: {e}")
            return {'success': False, 'message': str(e), 'members': [], 'group_title': ''}
        finally:
            if client:
                await client.disconnect()

    # ─────────────────────────────────────────────────────────────
    # لیچ دسته‌جمعی + ذخیره در دیتابیس
    # ─────────────────────────────────────────────────────────────

    async def bulk_leech_and_save(
        self,
        session_paths: List[str],
        group_link: str,
        total_target: int,
        owner_user_id: int,
        db: 'Database',
        filter_verified: bool = True,
        fetch_bio: bool = True,
        fetch_photos: bool = True,
        progress_callback=None,
        cancel_flag: Optional[Dict] = None,
    ) -> Dict:
        """
        لیچ دسته‌جمعی با چند اکانت و ذخیره مستقیم در دیتابیس.

        - سشن‌های نامعتبر خودکار inactive می‌شوند
        - seen_ids فقط بین اکانت‌های موفق share می‌شود
          (هر اکانت جدید می‌تواند پروفایل‌های تازه پیدا کند)
        """
        total_accounts = len(session_paths)
        if total_accounts == 0:
            return {'success': False, 'message': 'هیچ اکانتی انتخاب نشده', 'saved_count': 0}

        per_account = max(1, (total_target // total_accounts) + 10)

        saved_count = 0
        failed_accounts = 0
        invalid_sessions = 0
        accounts_used = 0
        group_title = ''

        # seen_ids فقط برای جلوگیری از ذخیره تکراری در دیتابیس
        # هر اکانت مستقل اسکن می‌کند — seen_ids را share نمی‌کنیم
        # تا هر اکانت بتواند پروفایل‌های جدید پیدا کند
        global_seen_ids: Set[int] = set()  # فقط برای جلوگیری از ذخیره تکراری

        for idx, session_path in enumerate(session_paths, 1):
            if cancel_flag and cancel_flag.get('cancelled'):
                logger.info("لیچ توسط کاربر لغو شد")
                break

            if saved_count >= total_target:
                break

            accounts_used = idx
            remaining = total_target - saved_count

            if progress_callback:
                await progress_callback(
                    idx, total_accounts,
                    f"اکانت {idx}/{total_accounts} | ذخیره شده: {saved_count}/{total_target}"
                )

            # هر اکانت با seen_ids خالی اسکن می‌کند تا پروفایل‌های جدید پیدا کند
            # global_seen_ids فقط موقع ذخیره چک می‌شود
            result = await self.get_group_members(
                session_path=session_path,
                group_link=group_link,
                limit=min(per_account, remaining + 10),
                msg_scan_limit=max(3000, per_account * 20),
                filter_verified=filter_verified,
                fetch_bio=fetch_bio,
                fetch_photos=fetch_photos,
                owner_user_id=owner_user_id,
                db=db,
                seen_ids=set(),  # هر اکانت مستقل — تکراری در ذخیره چک می‌شود
            )

            if not result['success']:
                msg = result['message']
                logger.error(f"اکانت {idx} ناموفق: {msg}")
                failed_accounts += 1

                # سشن نامعتبر → inactive در دیتابیس
                if 'سشن نامعتبر' in msg or 'unauthorized' in msg.lower():
                    invalid_sessions += 1
                    try:
                        account = await db.get_account_by_session(session_path)
                        if account:
                            await db.update_account_status(account.id, 'inactive')
                            logger.info(f"سشن {session_path} به inactive تغییر یافت")
                    except Exception as e:
                        logger.warning(f"خطا در inactive کردن سشن: {e}")
                continue

            if not group_title:
                group_title = result.get('group_title', '')

            # ذخیره در دیتابیس — فقط پروفایل‌هایی که قبلاً ذخیره نشدن
            new_saved = 0
            for member in result['members']:
                if cancel_flag and cancel_flag.get('cancelled'):
                    break
                if saved_count >= total_target:
                    break
                if member['user_id'] in global_seen_ids:
                    continue

                global_seen_ids.add(member['user_id'])

                profile_id = await db.save_leeched_profile(
                    owner_user_id=owner_user_id,
                    telegram_user_id=member['user_id'],
                    access_hash=member['access_hash'],
                    first_name=member.get('first_name'),
                    last_name=member.get('last_name'),
                    username=member.get('username'),
                    bio=member.get('bio'),
                    photos=member.get('photos', []),
                    source_group=group_link,
                )

                if profile_id:
                    saved_count += 1
                    new_saved += 1

            logger.info(f"اکانت {idx}: {new_saved} پروفایل جدید ذخیره شد")

            if idx < total_accounts and saved_count < total_target:
                delay = Config.DELAY_BETWEEN_ACTIONS + random.randint(0, Config.DELAY_RANDOM_RANGE)
                await asyncio.sleep(delay)

        return {
            'success': True,
            'saved_count': saved_count,
            'target': total_target,
            'accounts_used': accounts_used,
            'failed_accounts': failed_accounts,
            'invalid_sessions': invalid_sessions,
            'group_title': group_title,
            'message': f'{saved_count} پروفایل ذخیره شد از {accounts_used} اکانت'
                       + (f' ({invalid_sessions} سشن نامعتبر غیرفعال شد)' if invalid_sessions else ''),
        }
