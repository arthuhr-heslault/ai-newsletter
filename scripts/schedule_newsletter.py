import schedule
import time
from datetime import datetime
import subprocess
import sys
import os

def run_newsletter():
    print(f"Running newsletter at {datetime.now()}")
    subprocess.run([sys.executable, "scripts/weekly_report.py"])

def main():
    # Schedule for every Friday at 1 PM
    schedule.every().friday.at("13:00").do(run_newsletter)
    
    # Special one-time run for today at 10:15
    today = datetime.now()
    if today.hour < 10 or (today.hour == 10 and today.minute < 15):
        schedule.every().day.at("10:15").do(run_newsletter)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
