# tout.py
import pika
import json
import time

class MessageTimeout:
    def __init__(self):
        # RabbitMQ connection
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='user_input')
        self.channel.queue_declare(queue='system_output')
        
        # Set timeout duration (in seconds)
        self.timeout_duration = 30
        self.last_message_time = time.time()

    def check_timeout(self):
        current_time = time.time()
        if current_time - self.last_message_time > self.timeout_duration:
            print("Session timeout. No messages received for 30 seconds.")
            self.connection.close()
            return True
        return False

    def process_message(self, ch, method, properties, body):
        # Reset timer when message received
        self.last_message_time = time.time()
        
        # Process message (can be extended based on requirements)
        message = json.loads(body.decode())
        print(f"Message received: {message['message']}")

    def run(self):
        # Listen to both queues
        self.channel.basic_consume(
            queue='user_input',
            on_message_callback=self.process_message,
            auto_ack=True
        )
        self.channel.basic_consume(
            queue='system_output',
            on_message_callback=self.process_message,
            auto_ack=True
        )
        
        print("Timeout monitor is running. Waiting for messages...")
        
        try:
            while not self.check_timeout():
                self.connection.process_data_events()
                time.sleep(1)
        except KeyboardInterrupt:
            print("Timeout monitor stopped by user")
            self.connection.close()

if __name__ == "__main__":
    timeout_monitor = MessageTimeout()
    timeout_monitor.run()
