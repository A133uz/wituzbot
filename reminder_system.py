from celery import Celery

from datetime import datetime, timedelta, timezone
import asyncio
import logging
from sqlalchemy.orm import Session

from app.database.config import DatabaseSettings
from app.bot.config import MainBotSettings
from app.database.database import get_sync_session
from app.database.models import Event

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
    # task_routes={
    #     'reminder_system.send_reminder_task': {'queue': 'reminders'},
    # },
    worker_pool='gevent',  # or 'gevent' or 'eventlet'
    worker_concurrency=10,
)


    
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Check every minute for reminders that need to be sent
    sender.add_periodic_task(
        60.0,  # Every 60 seconds
        check_pending_reminders.s(),
        name='check for pending reminders'
    )

@celery_app.task
def check_pending_reminders():
    """Periodic task that checks if any reminders need to be sent"""
    logging.info("🔍 Checking for pending reminders...")
    
    try:
        with get_sync_session() as db:
            now = datetime.now(timezone.utc)
            logging.info(f"Current time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            
            events = db.query(Event).filter(
                Event.reminder_sent == False,
                Event.celery_task_id != None  
            ).all()
            
            logging.info(f"Found {len(events)} events to check")
            
            for event in events:
                logging.info(f"\n--- Checking Event {event.id}: {event.title} ---")
                
                
                event_dt = event.date_time
                logging.info(f"Event datetime (raw): {event_dt} (tzinfo: {event_dt.tzinfo})")
                
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                    logging.info(f"Added UTC timezone: {event_dt}")
                
                
                if event_dt <= now:
                    logging.info(f"❌ Event {event.id} is in the past, skipping")
                    continue
                
                logging.info(f"Event time: {event_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                
                reminder_time = event_dt - timedelta(hours=24)
                logging.info(f"Reminder should fire at: {reminder_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                time_diff = reminder_time - now
                logging.info(f"Time until reminder: {time_diff}")
                
                
                grace_period_start = now - timedelta(minutes=2)
                
                logging.info(f"Checking: {reminder_time} <= {now} and {reminder_time} > {grace_period_start}")
                
                if reminder_time <= now and reminder_time > grace_period_start:
                    logging.info(f"🔔 ✅ TIME TO SEND! Triggering reminder for event {event.id}!")
                    send_reminder_task.delay(event.id)
                else:
                    if reminder_time > now:
                        logging.info(f"⏳ Too early - reminder in {time_diff}")
                    else:
                        logging.info(f"⏰ Too late - reminder was {abs(time_diff)} ago")
            
            logging.info(f"\n✅ Check complete. Checked {len(events)} events.")
            
    except Exception as e:
        logging.error(f"❌ Error checking reminders: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

@celery_app.task(bind=True, max_retries=3)
def send_reminder_task(self, event_id: int):
    """Send reminder for an event"""
    logging.info(f"🔥 EXECUTING REMINDER TASK for event {event_id}")
    
    db = None
    try:
        with get_sync_session() as db:
            event = db.query(Event).filter(Event.id == event_id).first()
            
            if not event:
                logging.error(f"Event {event_id} not found")
                return f"Event {event_id} not found"
            
            if event.reminder_sent:
                logging.info(f"Reminder for event {event_id} already sent")
                return f"Reminder already sent for event {event_id}"
            
            event_dt = event.date_time
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            
            # Check if event is still in the future (safety check)
            now_utc = datetime.now(timezone.utc)
            if event_dt <= now_utc:
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
        if db:
            db.rollback()
        
        # Retry with exponential backoff
        raise self.retry(
            exc=exc, 
            countdown=min(300 * (2 ** self.request.retries), 3600),
            max_retries=3
        )

async def send_telegram_reminder(event: Event):
    """Send reminder message via Telegram"""
    try:
        from aiogram import Bot
        bot = Bot(token=bot_settings.TG_TOKEN)
        
        
        # Format reminder message
        message = f"🔔 <b>Event Reminder!</b>\n\n"
        message += f"📝 <b>{event.title}</b>\n"
        message += f"📅 <b>Tomorrow:</b> {event.local_datetime.strftime('%Y-%m-%d at %H:%M')}\n\n"
        
        if event.desc:
            message += f"📄 <b>Description:</b>\n{event.desc}\n\n"
        
        message += f"⏰ <i>This event starts in approximately 24 hours!</i>"
        
        # Send message via bot
        for reg in event.registrations:
            await bot.send_message(
                chat_id=reg.user_id,
                text=message,
                parse_mode="HTML"
            )
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to send telegram message: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return False
        

def _auto_schedule_reminder(event: Event, db: Session):
    """
    Mark event as having a scheduled reminder
    (Actual sending handled by periodic checker)
    """
    event_dt = event.date_time
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
        
    reminder_datetime = event_dt - timedelta(hours=24)
    now_utc = datetime.now(timezone.utc)
    
    if reminder_datetime < now_utc:
        logging.info(f"Event {event.id} is less than 24 hours away - no reminder scheduled")
        return None
    
    # Just mark that this event should have a reminder
    # The periodic task will actually send it at the right time
    event.celery_task_id = f"scheduled_{event.id}"  # Placeholder to mark as scheduled
    db.commit()
    
    logging.info(
        f"🕐 Reminder marked for periodic check - event {event.id} "
        f"will be reminded at {reminder_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    
    return event.celery_task_id

def update_event_and_reschedule(event: Event, db: Session):
    """Update event and reschedule reminder"""
    _cancel_reminder(event, db)
    
    # Reset reminder status
    event.reminder_sent = False
    
    # Schedule new
    return _auto_schedule_reminder(event, db)

def _cancel_reminder(event: Event, db: Session):
    """Cancel existing reminder"""
    if event.celery_task_id:
        event.celery_task_id = None
        db.commit()
        logging.info(f"Cancelled reminder for event {event.id}")