import requests
import os
from dotenv import load_dotenv; load_dotenv()
import argparse
import json


parser = argparse.ArgumentParser()
parser.add_argument('--message')
parser.add_argument('--chat_history', default=None, help="path to chat history")
parser.add_argument('--save_chat', default=True)
parser.add_argument('--system_prompt', default=None)
args = parser.parse_args()


def main():
    url = 'https://api.venice.ai/api/v1/chat/completions'
    headers = {'Authorization': f'Bearer {os.environ["VENICE_API_KEY"]}', 'Content-Type': 'application/json'}
    data = {
        "frequency_penalty": 0,
        "n": 1,
        "presence_penalty": 0,
        "temperature": 0.7,
        "top_p": 0.9,
        "venice_parameters": {
            "include_venice_system_prompt": False
        },
        "parallel_tool_calls": False,
        "model": "venice-uncensored",
        "messages": []
    }
    if args.chat_history is not None:
        with open(args.chat_history, 'r') as f:
            chat = f.read()
            chat = json.loads(chat)
        data['messages'] = chat
    if args.system_prompt:
        system_prompt = {
            "content": args.system_prompt,
            "role": "system"
        }
        data["messages"].append(system_prompt)
    user_message = {
        "content": args.message,
        "role": "user"
    }
    data['messages'].append(user_message)
    print(data)
    response = requests.post(url=url, headers=headers, json=data)
    print(response.content)
    response = response.json()['choices'][0]['message']['content']
    print(response)
    if args.save_chat:
        data['messages'].append({
            "content": response,
            "role": "assistant"
        })
        with open(args.chat_history, "w", encoding="utf-8") as f:
            json.dump(data['messages'], f, indent=4)        
        
if __name__ == "__main__":
    main()
