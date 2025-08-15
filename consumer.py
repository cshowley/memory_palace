import requests
import os
import json
import pika
import threading
from dotenv import load_dotenv
load_dotenv()


# Global state: {chat_history_path: {"messages": [...], "active": True, "inactivity_timer": Timer}}
buffers = {}  # Primary 30s message buffer
inactivity_timers = {}  # Secondary 10m timer for idle chats

textify_sysprompt = open('./prompts/text_message_rewrite.txt').read().strip()
def process_batch(chat_path):
    # Process buffered messages (30s batch)
    global buffers, inactivity_timers
    
    buffer = buffers.get(chat_path, {"messages": []})
    
    try:
        # Load full chat history
        if os.path.exists(chat_path):
            with open(chat_path, "r", encoding="utf-8") as f:
                chat = json.load(f)
        else:
            chat = []
        
        # Append buffered messages
        chat.extend(buffer["messages"])
        
        # Send to LLM
        url = "https://api.venice.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ['VENICE_API_KEY']}", "Content-Type": "application/json"}
        payload = {
            "model": "venice-uncensored",
            "messages": chat,
            "temperature": 0.7,
            "top_p": 0.9,
            "n": 1,
            "venice_parameters": {"include_venice_system_prompt": False}
        }
        
        llm_response = requests.post(url, headers=headers, json=payload).json()
        assistant_content = llm_response["choices"][0]["message"]["content"]
        print(f"<<Raw>> LLM response for {chat_path}: {assistant_content}")
        def textify(message):
            payload = {
                "model": "venice-uncensored",
                "messages": [
                    {
                        "role":"system",
                        "content": textify_sysprompt
                    },
                    {
                        "role":"user",
                        "content": message
                    },    
                ],
                "temperature": 0.7,
                "top_p": 0.9,
                "n": 1,
                "venice_parameters": {"include_venice_system_prompt": False}
            }
            llm_response = requests.post(url, headers=headers, json=payload).json()
            text_content = llm_response["choices"][0]["message"]["content"]
            output = [message for message in text_content.split('\n') if message != '']
            return output
        

        assistant_content = textify(assistant_content)
        for message in assistant_content:
            # Append LLM response to chat history
            chat.append({"role": "assistant", "content": message})
            with open(chat_path, "w", encoding="utf-8") as f:
                json.dump(chat, f, indent=4)
        
        print(f"LLM response for {chat_path}: {assistant_content}")
    
    except Exception as e:
        print(f"Error in LLM processing: {e}")
    
    # Reset buffer
    buffers[chat_path] = {"messages": [], "timer": None}
    
    # Start 10m inactivity timer
    start_inactivity_timer(chat_path)

def start_inactivity_timer(chat_path):
    # Cancel existing timer if any
    if chat_path in inactivity_timers and inactivity_timers[chat_path]:
        inactivity_timers[chat_path].cancel()
    
    # Start new timer
    wait_time = 6000 # count of seconds until LLM response request is triggered for inactivity
    timer = threading.Timer(wait_time, trigger_inactive_chat, args=[chat_path])
    inactivity_timers[chat_path] = timer
    timer.start()

def trigger_inactive_chat(chat_path):
    # Force process the current chat history
    print(f"10m inactivity trigger for {chat_path}")
    process_batch(chat_path)

def on_message(channel, method, properties, body):
    try:
        msg_data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        print("Invalid JSON in message")
        channel.basic_ack(method.delivery_tag)
        return
    
    chat_path = msg_data.get("chat_history", "default.json")

    # Initialize buffer if not exists
    if chat_path not in buffers:
        buffers[chat_path] = {"messages": [], "timer": None}
    
    # Reset inactivity timer if we received a new message
    if chat_path in inactivity_timers and inactivity_timers[chat_path]:
        inactivity_timers[chat_path].cancel()
        inactivity_timers[chat_path] = None
    
    # Build message from payload
    new_messages = []
    if msg_data.get("system_prompt"):
        new_messages.append({"role": "system", "content": msg_data["system_prompt"]})
    if msg_data.get("message"):
        new_messages.append({"role": "user", "content": msg_data["message"]})
    
    # Append to buffer
    buffers[chat_path]["messages"].extend(new_messages)
    
    # Start 30s batch timer if not running
    batch_message_timer = 30
    if not buffers[chat_path]["timer"]:
        buffers[chat_path]["timer"] = threading.Timer(batch_message_timer, process_batch, args=[chat_path])
        buffers[chat_path]["timer"].start()
    
    channel.basic_ack(method.delivery_tag)

# RabbitMQ setup
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=pika.PlainCredentials("guest", "guest"),
    )
)
channel = connection.channel()
channel.queue_declare(queue="llm_messages", durable=True)

# Start consuming
channel.basic_consume(queue="llm_messages", on_message_callback=on_message, auto_ack=False)
print("Consumer started. Waiting for messages...")
channel.start_consuming()