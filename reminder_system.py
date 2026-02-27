from celery import Celery
from celery.result import AsyncResult

from datetime import datetime, timedelta, timezone
import asyncio
import logging
from sqlalchemy.orm import Session

from app.database.config import DatabaseSettings
from app.bot.config import MainBotSettings
from app.database.database import get_sync_session
from app.database.models import Event, EventReminder, Registration

from typing import List

logger = logging.getLogger(__name__)

settings = DatabaseSettings()
bot_settings = MainBotSettings()

celery_app = Celery(
    "reminder_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    worker_pool='gevent',  # or 'gevent' or 'eventlet'
    worker_concurrency=10,
)

BATCH_SIZE = 50


@celery_app.task(bind=True, max_retries=3)
def send_reminder_task(self, reminder_id: int):
    """Send reminder for an event"""
    logging.info(f"🔥 EXECUTING REMINDER TASK for event")
    
    db = None
    try:
        with get_sync_session() as db:
            reminder = db.query(EventReminder).filter(EventReminder.id == reminder_id).first()
            
            if not reminder:
                logging.error(f"Reminder {reminder_id} not found")
                return f"Reminder {reminder_id} not found"
            
            if reminder.is_sent:
                logging.info(f"Reminder {reminder_id} already sent")
                return f"Reminder {reminder_id} already sent"
            
            event = reminder.event
            
            event_dt = event.date_time
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            
            now_utc = datetime.now(timezone.utc)
            if event_dt <= now_utc:
                logging.warning(f"Event {event.id} is in the past, skipping reminder")
                return f"Event {event.id} is in the past"
            
            registrations = db.query(Registration).filter(
                Registration.event_id == event.id
            ).all()
            
            if not registrations:
                logging.info(f"No registrations for event {event.id}, skipping reminder")
                reminder.is_sent = True
                db.commit()
                return f"No registrations for event {event.id}"
            
            user_ids = [reg.user_id for reg in registrations]
            
            total_sent = 0
            total_failed = 0
            
            for i in range(0, len(user_ids), BATCH_SIZE):
                batch = user_ids[i:i+BATCH_SIZE]
                
                try:
                    sent, failed = asyncio.run(
                        send_reminder_batch(event, reminder, batch)
                    )
                    total_sent += sent
                    total_failed += failed
                    
                    logging.info(
                        f"Batch {i//BATCH_SIZE + 1}: "
                        f"sent {sent}, failed {failed}"
                    )
                    
                except Exception as e:
                    logging.error(f"Failed to send batch: {e}")
                    total_failed += len(batch) 
                                      
            reminder.is_sent = True
            db.commit()
            
            logging.info(
                f"✅ Reminder {reminder_id} completed: "
                f"sent {total_sent}, failed {total_failed}"
            )
            
            return f"Reminder sent: {total_sent} success, {total_failed} failed"
        
    except Exception as exc:
        logging.error(f"❌ Reminder task failed for reminder {reminder_id}: {str(exc)}")
        if db:
            db.rollback()
        
        # Retry with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=min(300 * (2 ** self.request.retries), 3600),
            max_retries=3
        )

async def send_reminder_batch(event: Event, reminder: EventReminder, user_ids: List[int]) -> tuple:
    """
    Send reminder to a batch of users
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    from aiogram import Bot
    
    try:
        bot = Bot(token=bot_settings.TG_TOKEN)
        
        hours_before = reminder.hours_before
        message = f"🔔 <b>Event Reminder!</b>\n\n"
        message += f"📝 <b>{event.title}</b>\n"
        message += f"📅 <b>Starting at </b> {event.date_time.strftime('%Y-%m-%d at %H:%M')}\n\n" 
        
        if reminder.message:
            message += reminder.message + "\n"
        else:
            message += f"📄 <b>Description:</b>\n{event.desc}\n\n"
        
        
        if event.location:
            message += f"📍 <b>Location:</b> {event.location}\n" 
        
        message += f"⏰ <i>This event starts in approximately {hours_before} {"hour" if hours_before == 1 else "hours" }!</i>"  
        
        sent_count = 0
        failed_count = 0
        for user_id in user_ids:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML"
                )
                sent_count += 1
                
            except Exception as e:
                logging.error(f"Failed to send reminder to user {user_id}: {e}")
                failed_count += 1
        
        await bot.session.close()
        
        return sent_count, failed_count
    
    except Exception as e:
        logging.error(f"Failed to send reminder batch: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return 0, len(user_ids)
            
    
def schedule_reminder(event: Event, reminder_config: dict, db: Session) -> str:
    """
    Schedule a reminder for an event
    
    Args:
        event: Event object
        reminder_config: Dict with 'hours_before' and optional 'message'
        db: Database session
    
    Returns:
        Celery task ID
    """
    event_dt = event.date_time
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
        
    hours_before = reminder_config.get('hours_before', 24)
    custom_message = reminder_config.get('message')
        
    reminder_dt = event_dt - timedelta(hours=hours_before)
    now_utc = datetime.now(timezone.utc)
    
    if reminder_dt < now_utc:
        logging.info(f"Event {event.id} is less than {hours_before} {"hour" if hours_before > 1 else "hours"} away - no reminder scheduled")
        return None
    
    reminder = EventReminder(
        event_id=event.id,
        hours_before=hours_before,
        message=custom_message,
        is_sent=False
    )
    
    db.add(reminder)
    db.flush()
    
    result = send_reminder_task.apply_async(
        args=[reminder.id],
        eta=reminder_dt
    )
    
    reminder.celery_task_id = result.id
    db.commit()
    
    logger.info(
        f"🕐 Reminder {reminder.id} scheduled for event {event.id} '{event.title}' "
        f"at {reminder_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
        f"({hours_before} hours before event) "
        f"(task_id: {result.id})"
    )
    
    return result.id
        

def update_reminder(reminder_id: int, reminder_config: dict, db: Session) -> str:
    """
    Update an existing reminder
    
    Args:
        reminder_id: EventReminder ID
        reminder_config: Dict with optional 'hours_before' and 'message'
        db: Database session
    
    Returns:
        New Celery task ID
    """
    reminder = db.query(EventReminder).filter(EventReminder.id == reminder_id).first()
    
    if not reminder:
        raise ValueError(f"Reminder {reminder_id} not found")
    
    if reminder.is_sent:
        logger.warning(f"Reminder {reminder_id} already sent, cannot update")
        return None
    
    if reminder.celery_task_id:
        try:
            from celery.result import AsyncResult
            AsyncResult(reminder.celery_task_id).revoke()
            logger.info(f"❌ Cancelled reminder task {reminder.celery_task_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke task {reminder.celery_task_id}: {e}")
    
    # Update reminder config
    if 'hours_before' in reminder_config:
        reminder.hours_before = reminder_config['hours_before']
    if 'message' in reminder_config:
        reminder.message = reminder_config['message']
    
    event = reminder.event
    event_dt = event.date_time
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
    
    reminder_dt = event_dt - timedelta(hours=reminder.hours_before)
    now_utc = datetime.now(timezone.utc)
    
    if reminder_dt < now_utc:
        logger.info(f"Reminder {reminder_id} time has passed, not rescheduling")
        reminder.celery_task_id = None
        db.commit()
        return None
    
    # Reschedule with new time
    result = send_reminder_task.apply_async(
        args=[reminder.id],
        eta=reminder_dt
    )
    
    reminder.celery_task_id = result.id
    db.commit()
    
    logger.info(
        f"🔄 Reminder {reminder_id} rescheduled "
        f"at {reminder_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
        f"(task_id: {result.id})"
    )
    
    return result.id

def _cancel_reminder(reminder_id: int, db: Session):
    """Cancel a scheduled reminder"""
    reminder = db.query(EventReminder).filter(EventReminder.id == reminder_id).first()
    
    if not reminder:
        logger.warning(f"Reminder {reminder_id} not found")
        return
    
    if reminder.is_sent:
        logger.info(f"Reminder {reminder_id} already sent, nothing to cancel")
        return
    
    if reminder.celery_task_id:
        try:
            from celery.result import AsyncResult
            AsyncResult(reminder.celery_task_id).revoke()
            logger.info(f"❌ Cancelled reminder {reminder_id} (task_id: {reminder.celery_task_id})")
        except Exception as e:
            logger.warning(f"Failed to revoke task {reminder.celery_task_id}: {e}")
    
    db.delete(reminder)
    db.commit()
    
def cancel_all_event_reminders(event_id: int, db: Session):
    """Cancel all reminders for an event"""
    reminders = db.query(EventReminder).filter(
        EventReminder.event_id == event_id,
        EventReminder.is_sent == False
    ).all()
    
    for reminder in reminders:
        _cancel_reminder(reminder.id, db)