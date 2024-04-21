import threading
import time
import json
import helper
from slack_bolt import App
import os
import logging

def worker(cache, app):
    print("Worker started")
    while True:
        # Simulate the worker checking every 60 seconds
        time.sleep(15)
        print("Worker running")

        for key in cache.scan_iter("request:*"):
            serialized_data = cache.get(key)
            if serialized_data:
                data = json.loads(serialized_data)
                
                # Check if the request is ready to be processed
                if data['status'] == 'ready':
                    # Notify the relevant teachers only once
                    for teacher_key in cache.scan_iter("teacher:*"):
                        teacher_name = cache.get(teacher_key).decode('utf-8')
                        teacher_id = teacher_key.decode('utf-8').split(':')[1]
                        if teacher_id == data['requester_id']:
                            continue  # Don't notify the requester
                        
                        response = app.client.conversations_open(users=[teacher_id])
                        dm_id = response["channel"]['id']
                        req = app.client.chat_postMessage(
                            channel=dm_id, 
                            text=f"Request:{data['requester_id']}, hello {teacher_name}! Can you substitute for {data['requester_name']}'s class? Thumbs up the message or reply yes."
                        )
                        logging.info(req)
                    
                    # Update the request status to 'processed' to prevent re-notification
                    data['status'] = 'processed'
                    cache.setex(key, 604800, json.dumps(data))  # Reset the TTL for another week

if __name__ == "__main__":
    cache = helper.set_up_cache_local()
    app = App(token=os.environ["SLACK_BOT_TOKEN"])
    threading.Thread(target=worker, args=(cache, app)).start()