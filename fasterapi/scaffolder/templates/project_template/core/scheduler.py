import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

scheduler = AsyncIOScheduler()

if (os.getenv("DB_TYPE") or "mongodb").strip().lower() == "mongodb":
    from apscheduler.jobstores.mongodb import MongoDBJobStore
    from pymongo import MongoClient

    mongo_client = MongoClient(os.getenv("MONGO_URL") or "mongodb://localhost:27017")
    scheduler.add_jobstore(MongoDBJobStore(database="apscheduler", collection="background_jobs", client=mongo_client))
# Other databases use APScheduler's in-memory job store: jobs added at runtime do not survive a restart.

# EXAMPLE CODE FOR ADDING JOB
# scheduler.add_job(alarm, "date", run_date=alarm_time, args=[datetime.now()])
# alarm is a function, "date" is the trigger and run_date is the time for the trigger to happen
