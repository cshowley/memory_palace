# memory_palace

persistent memory for llm chats
support for multi-message inputs to LLM, and multiple responses

Start local rabbitmq instance:
rabbitmq-server

Start consumer process to receive user messages and send to consumer in batches:
uv run consumer.py

Send requests to consumer using producer process; messages will queue and all be sent to consumer after a certain amount of time, and llm response will be written to chat history json file
e.g.
uv run producer.py --system_prompt "sysprompt" --message "message 1" --chat_history "history.json"
uv run producer.py --message "message 2" --chat_history "history.json"
uv run producer.py --message "message 3" --chat_history "history.json"
