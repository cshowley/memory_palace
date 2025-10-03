import argparse
import json
import pika


def send_to_rabbitmq(
    chat_history_path, message, system_prompt=None, instant_reply=False
):
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Declare queue
    channel.queue_declare(queue="llm_messages", durable=True)

    # Create message payload
    msg_data = {
        "chat_history": chat_history_path,
        "message": message,
        "system_prompt": system_prompt,
    }

    # Send to queue
    channel.basic_publish(
        exchange="",
        routing_key="llm_messages",
        body=json.dumps(msg_data),
        properties=pika.BasicProperties(delivery_mode=2),  # Persistent message
    )
    connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    parser.add_argument(
        "--chat_history", default="chat_history.json", help="Path to chat history"
    )
    parser.add_argument("--save_chat", action="store_true", default=True)
    parser.add_argument("--system_prompt", default=None)
    parser.add_argument("--instant_reply", action="store_true", default=False)
    args = parser.parse_args()

    # Instead of calling LLM directly, send to RabbitMQ
    print(args)
    send_to_rabbitmq(
        chat_history_path=args.chat_history,
        message=args.message,
        system_prompt=args.system_prompt,
        instant_reply=args.instant_reply,
    )
    print(f"Message sent to queue. Use consumer script to process.")


if __name__ == "__main__":
    main()
