"""ماژول مدیریت بلاک و انبلاک کاربران"""
import logging
import asyncio
import random
from typing import Optional, Dict, List
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from pathlib import Path

from src.config import Config

logger = logging.getLogger(__name__)

class BlockManager:
    """کلاس مدیریت بلاک و انبلاک"""
    
    def __init__(self, api_id: Optional[int] = None, api_hash: Optional[str] = None):
        """مقداردهی اولیه"""
        self.api_id = api_id or Config.API_ID
        self.api_hash = api_hash or Config.API_HASH
    
    async def block_user(self, session_path: str, target: str) -> Dict[str, any]:
        """
        بلاک کردن کاربر
        
        Args:
            session_path: مسیر فایل سشن
            target: یوزرنیم یا آیدی کاربر
            
        Returns:
            دیکشنری حاوی وضعیت
        """
        client = None
        
        try:
            # بارگذاری سشن
            session_string = Path(session_path).read_text(encoding='utf-8')
            
            client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                return {
                    'success': False,
                    'message': 'سشن نامعتبر است'
                }
            
            try:
                # دریافت entity کاربر
                user = await client.get_entity(target)
                
                # بلاک کردن
                await client(functions.contacts.BlockRequest(id=user))
                
                logger.info(f"کاربر {target} بلاک شد")
                
                return {
                    'success': True,
                    'message': 'کاربر با موفقیت بلاک شد',
                    'target': target,
                    'user_id': user.id
                }
                
            except Exception as e:
                logger.error(f"خطا در بلاک کردن: {e}")
                return {
                    'success': False,
                    'message': f'خطا: {str(e)}'
                }
            
        except Exception as e:
            logger.exception(f"خطا در بلاک: {e}")
            return {
                'success': False,
                'message': f'خطا: {str(e)}'
            }
        
        finally:
            if client:
                await client.disconnect()
    
    async def unblock_user(self, session_path: str, target: str) -> Dict[str, any]:
        """
        انبلاک کردن کاربر
        
        Args:
            session_path: مسیر فایل سشن
            target: یوزرنیم یا آیدی کاربر
            
        Returns:
            دیکشنری حاوی وضعیت
        """
        client = None
        
        try:
            # بارگذاری سشن
            session_string = Path(session_path).read_text(encoding='utf-8')
            
            client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                return {
                    'success': False,
                    'message': 'سشن نامعتبر است'
                }
            
            try:
                # دریافت entity کاربر
                user = await client.get_entity(target)
                
                # انبلاک کردن
                await client(functions.contacts.UnblockRequest(id=user))
                
                logger.info(f"کاربر {target} انبلاک شد")
                
                return {
                    'success': True,
                    'message': 'کاربر با موفقیت انبلاک شد',
                    'target': target,
                    'user_id': user.id
                }
                
            except Exception as e:
                logger.error(f"خطا در انبلاک کردن: {e}")
                return {
                    'success': False,
                    'message': f'خطا: {str(e)}'
                }
            
        except Exception as e:
            logger.exception(f"خطا در انبلاک: {e}")
            return {
                'success': False,
                'message': f'خطا: {str(e)}'
            }
        
        finally:
            if client:
                await client.disconnect()
    
    async def bulk_block(self, session_paths: List[str], target: str,
                        progress_callback=None, workers: int = 1, custom_delay: int = None) -> Dict[str, any]:
        """
        بلاک دسته‌جمعی
        
        Args:
            session_paths: لیست مسیر فایل‌های سشن
            target: یوزرنیم یا آیدی کاربر
            progress_callback: تابع callback برای نمایش پیشرفت
            workers: تعداد اکانت‌های همزمان
            custom_delay: تاخیر سفارشی (None = استفاده از تاخیر پیش‌فرض)
            
        Returns:
            دیکشنری حاوی نتایج
        """
        results = {
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        total = len(session_paths)
        
        # اجرای همزمان با worker
        for i in range(0, total, workers):
            batch = session_paths[i:i + workers]
            tasks = []
            
            for session_path in batch:
                tasks.append(self.block_user(session_path, target))
            
            # اجرای همزمان batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # پردازش نتایج
            for j, result in enumerate(batch_results):
                index = i + j + 1
                
                if isinstance(result, Exception):
                    result = {'success': False, 'message': str(result)}
                
                if result['success']:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append({
                    'session': Path(batch[j]).name,
                    'result': result
                })
                
                # بروزرسانی پیشرفت
                if progress_callback:
                    await progress_callback(index, total, f"در حال بلاک {index}/{total}...")
            
            # تاخیر بین batch‌ها (به جز آخرین batch)
            if i + workers < total:
                if custom_delay is not None:
                    delay = custom_delay
                else:
                    delay = Config.DELAY_BETWEEN_ACTIONS + random.randint(0, Config.DELAY_RANDOM_RANGE)
                
                logger.info(f"صبر {delay} ثانیه قبل از batch بعدی...")
                await asyncio.sleep(delay)
        
        return results
    
    async def bulk_unblock(self, session_paths: List[str], target: str,
                          progress_callback=None, workers: int = 1, custom_delay: int = None) -> Dict[str, any]:
        """
        انبلاک دسته‌جمعی
        
        Args:
            session_paths: لیست مسیر فایل‌های سشن
            target: یوزرنیم یا آیدی کاربر
            progress_callback: تابع callback برای نمایش پیشرفت
            workers: تعداد اکانت‌های همزمان
            custom_delay: تاخیر سفارشی (None = استفاده از تاخیر پیش‌فرض)
            
        Returns:
            دیکشنری حاوی نتایج
        """
        results = {
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        total = len(session_paths)
        
        # اجرای همزمان با worker
        for i in range(0, total, workers):
            batch = session_paths[i:i + workers]
            tasks = []
            
            for session_path in batch:
                tasks.append(self.unblock_user(session_path, target))
            
            # اجرای همزمان batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # پردازش نتایج
            for j, result in enumerate(batch_results):
                index = i + j + 1
                
                if isinstance(result, Exception):
                    result = {'success': False, 'message': str(result)}
                
                if result['success']:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append({
                    'session': Path(batch[j]).name,
                    'result': result
                })
                
                # بروزرسانی پیشرفت
                if progress_callback:
                    await progress_callback(index, total, f"در حال انبلاک {index}/{total}...")
            
            # تاخیر بین batch‌ها (به جز آخرین batch)
            if i + workers < total:
                if custom_delay is not None:
                    delay = custom_delay
                else:
                    delay = Config.DELAY_BETWEEN_ACTIONS + random.randint(0, Config.DELAY_RANDOM_RANGE)
                
                logger.info(f"صبر {delay} ثانیه قبل از batch بعدی...")
                await asyncio.sleep(delay)
        
        return results
