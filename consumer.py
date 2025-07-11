import pika
import json
import requests
import threading
from dotenv import load_dotenv
import os

load_dotenv()
VENICE_API_KEY = os.getenv("VENICE_API_KEY")

# Global buffer by chat history
buffers = {}  # {chat_history_path: {"messages": [], "timer": None}}

def process_batch(chat_history_path):
    global buffers
    buffer = buffers.get(chat_history_path)
    if not buffer or not buffer["messages"]:
        return

    try:
        # Load existing chat
        if os.path.exists(chat_history_path):
            with open(chat_history_path, 'r') as f:
                chat = json.load(f)
        else:
            chat = []

        # Append buffered messages to chat
        chat.extend(buffer["messages"])
        
        # Send to LLM
        url = 'https://api.venice.ai/api/v1/chat/completions'
        headers = {'Authorization': f'Bearer {VENICE_API_KEY}', 'Content-Type': 'application/json'}
        data = {
            "model": "venice-uncensored",
            "messages": chat,
            "temperature": 0.7,
            "top_p": 0.9,
            "n": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "parallel_tool_calls": False,
            "venice_parameters": {"include_venice_system_prompt": False}
        }
        
        response = requests.post(url=url, headers=headers, json=data).json()
        assistant_response = response['choices'][0]['message']['content']
        
        # Append response to chat
        chat.append({"role": "assistant", "content": assistant_response})
        
        # Save chat history
        with open(chat_history_path, "w", encoding="utf-8") as f:
            json.dump(chat, f, indent=4)
            
        print("Processed batch for", chat_history_path)
        
    except Exception as e:
        print(f"Error processing {chat_history_path}:", e)
    
    # Reset buffer and timer
    buffers[chat_history_path]["messages"] = []
    buffers[chat_history_path]["timer"] = None

def on_message(channel, method, properties, body):
    msg_data = json.loads(body.decode('utf-8'))
    chat_path = msg_data["chat_history"]
    
    # Initialize buffer for this chat if not exists
    if chat_path not in buffers:
        buffers[chat_path] = {"messages": [], "timer": None}
    
    # Add system prompt if provided
    if msg_data["system_prompt"]:
        buffers[chat_path]["messages"].append({
            "role": "system",
            "content": msg_data["system_prompt"]
        })
    
    # Add user message
    buffers[chat_path]["messages"].append({
        "role": "user",
        "content": msg_data["message"]
    })
    
    # Start timer if not already running
    if buffers[chat_path]["timer"] is None:
        buffers[chat_path]["timer"] = threading.Timer(30, process_batch, args=[chat_path])
        buffers[chat_path]["timer"].start()
    
    # Acknowledge receipt (not final processing)
    channel.basic_ack(method.delivery_tag)

# RabbitMQ setup
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='llm_messages', durable=True)

# Start consuming
channel.basic_consume(queue='llm_messages', on_message_callback=on_message)
print("Consumer waiting for messages...")
channel.start_consuming()