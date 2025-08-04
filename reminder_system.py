from celery import Celery

from datetime import datetime, timedelta, timezone
import asyncio
import logging
from sqlalchemy.orm import Session

from app.database.config import settings
from app.database.database import get_sync_session
from app.database.models import Event

celery_app = Celery(
    "reminder_system",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_routes={
        'send_reminder_task': {'queue': 'reminders'},
    }
)

bot_instance = None

def init_bot(bot):
    global bot_instance
    bot_instance = bot
    
@celery_app.task(bind=True, max_retries=3)
def send_reminder_task(self, event_id: int):
    
    
    try:
        with get_sync_session() as db:
        
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                logging.error(f"Event {event_id} not found")
                return f"Event {event_id} not found"
            
            if event.reminder_sent:
                logging.info(f"Reminder for event {event_id} already sent")
                return f"Reminder already sent for event {event_id}"
            
            # Check if event is still in the future (safety check)
            if event.date_time <= datetime.now(timezone.utc):
                logging.warning(f"Event {event_id} is in the past, skipping reminder")
                return f"Event {event_id} is in the past"
            
            # Send the reminder automatically
            success = asyncio.run(send_telegram_reminder(event))
            
            if success:
                # Mark reminder as sent
                event.reminder_sent = True
                db.commit()
                logging.info(f"✅ Automatic reminder sent for event {event_id}: '{event.title}'")
                return f"Reminder sent for event {event_id}"
            else:
                # Retry if sending failed
                db.rollback()
                raise Exception("Failed to send telegram message")
        
    except Exception as exc:
        logging.error(f"❌ Reminder task failed for event {event_id}: {str(exc)}")
        db.rollback()
        
        # Retry with exponential backoff
        raise self.retry(
            exc=exc, 
            countdown=min(300 * (2 ** self.request.retries), 3600),  # Max 1 hour
            max_retries=3
        )
        
async def send_telegram_reminder(event : Event):
    try:
        if not bot_instance:
            logging.error("Bot instance not initialized")
            return False
        
        # Format reminder message
        message = f"🔔 <b>Event Reminder!</b>\n\n"
        message += f"📝 <b>{event.title}</b>\n"
        message += f"📅 <b>Tomorrow:</b> {event.date_time.strftime('%Y-%m-%d at %H:%M')}\n\n"
        
        if event.description:
            message += f"📄 <b>Description:</b>\n{event.desc}\n\n"
        
        message += f"⏰ <i>This event starts in approximately 24 hours!</i>"
        
        # Send message via bot
        await bot_instance.SendMessage(
            chat_id=event.user_id,
            text=message,
            parse_mode="HTML"
        )
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to send telegram message: {str(e)}")
        return False
    
@staticmethod
def _auto_schedule_reminder(event: Event, db: Session):
        """
        AUTOMATICALLY schedule reminder task - this is the key automation
        """
        # Calculate exact time to send reminder (24 hours before)
        event_dt = event.date_time
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
            
        reminder_datetime = event_dt - timedelta(hours=24)
        
        # Only schedule if reminder time is in the future
        if reminder_datetime <= datetime.now(timezone.utc):
            logging.info(f"Event {event.id} is less than 24 hours away - no reminder scheduled")
            return None
        
        # This is where the magic happens - schedule the task to run automatically
        task = send_reminder_task.apply_async(
            args=[event.id],
            eta=reminder_datetime  # Celery will automatically execute at this exact time
        )
        
        # Store task ID for potential cancellation
        event.celery_task_id = task.id
        db.commit()
        
        logging.info(
            f"🕐 Automatic reminder scheduled for event {event.id} "
            f"at {reminder_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        return task.id
    
@staticmethod
def update_event_and_reschedule(
    event: Event, db: Session
):
        _cancel_reminder(event, db)
        
        # Reset reminder status
        event.reminder_sent = False
        
        # Schedule new
        return _auto_schedule_reminder(event, db)

@staticmethod
def _cancel_reminder(event: Event, db: Session):
        """Cancel existing reminder task"""
        if event.celery_task_id:
            send_reminder_task.AsyncResult(event.celery_task_id).revoke()
            event.celery_task_id = None
            db.commit()
            logging.info(f"Cancelled reminder for event {event.id}")