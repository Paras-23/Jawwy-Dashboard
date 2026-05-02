import time
import subprocess
from pymongo import MongoClient, ReturnDocument
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIG ----
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "Jawwy"
COLLECTION = "Logs"

MACHINE_NAME = os.getenv("MACHINE_NAME", "worker_1")

MAX_PROCESSES = 8
PROCESS_CHECK_INTERVAL = 1
JOB_POLL_INTERVAL = 2

# ---- DB ----
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION]

active_processes = []


# ---- CLEANUP FINISHED PROCESSES ----
def cleanup_processes():
    global active_processes
    active_processes = [
        (p, job_id) for (p, job_id) in active_processes if p.poll() is None
    ]

# ---- RESET STUCK JOBS (CRASH RECOVERY) ----
def reset_stuck_jobs():
    now = datetime.now(timezone.utc)

    result = collection.update_many(
        {
            "status": "processing",
            "lock_until": {"$lt": now}
        },
        {
            "$set": {
                "status": "pending",
                "worker": None
            },
            "$unset": {
                "lock_until": ""
            }
        }
    )

    if result.modified_count > 0:
        print(f"♻️ Reset {result.modified_count} expired jobs")


print("TOTAL:", collection.count_documents({}))
print("PENDING:", collection.count_documents({"status": "pending"}))
print("SAMPLE:", collection.find_one())

# ---- PICK ONE JOB (ATOMIC + SAFE) ----
def get_job():
    now = datetime.now(timezone.utc)
    lease_time = now + timedelta(minutes=10)

    job = collection.find_one_and_update(
        {
            "status": "pending",
            "ga": {"$exists": True}
        },
        {
            "$set": {
                "status": "processing",
                "worker": MACHINE_NAME,
                "updated_at": now,
                "lock_until": lease_time
            }
        },
        return_document=ReturnDocument.AFTER
    )

    print("JOB:", job)
    return job


# ---- RUN TRAFFIC ----
def run_job(job):
    ga = job.get("ga")
    ua = job.get("ua", "")
    gs = job.get("gs", "")
    url = job.get("u", "")

    print(f"🚀 [{MACHINE_NAME}] Running GA: {ga}")

    try:
        p = subprocess.Popen([
            "python",
            "traffic.py",
            ga,
            ua,
            gs,
            url if url else "https://www.jawwy.sa/content/jawwy/ar/shop.html"
        ])

        active_processes.append({
                "process": p,
                "job_id": job["_id"],
                "start_time": time.time()
            })

    except Exception as e:
        print("❌ Error starting traffic:", e)


# ---- MARK DONE ----
def mark_done(job_id, duration):
    result = collection.update_one(
        {
            "_id": job_id,
            "worker": MACHINE_NAME
        },
        {
            "$set": {
                "status": "done",
                "updated_at": datetime.now(timezone.utc),
                "session_duration": duration
            },
            "$unset": {
                "lock_until": ""
            }
        }
    )

    if result.modified_count == 0:
        print(f"⚠️ Skipped marking done (not owner) {job_id}")


# ---- CHECK COMPLETED PROCESSES ----
def check_completed():
    global active_processes

    still_running = []

    for item in active_processes:
        p = item["process"]
        job_id = item["job_id"]
        start_time = item["start_time"]

        if p.poll() is None:
            still_running.append(item)
        else:
            end_time = time.time()
            duration = round(end_time - start_time, 2)

            mark_done(job_id, duration)

            print(f"✅ Completed job {job_id} in {duration}s")

    active_processes = still_running


# ---- MAIN LOOP ----
print(f"🚀 Worker started: {MACHINE_NAME}")

while True:
    try:
        check_completed()
        reset_stuck_jobs()

        if len(active_processes) >= MAX_PROCESSES:
            time.sleep(PROCESS_CHECK_INTERVAL)
            continue

        job = get_job()

        if not job:
            time.sleep(JOB_POLL_INTERVAL)
            continue

        run_job(job)

    except Exception as e:
        print("❌ Worker error:", e)
        time.sleep(2)