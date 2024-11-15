# dialogue.py
import pika
import json
import openai
import time
import yaml

class DialogueSystem:
    def __init__(self):
        # Load config
        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Initialize OpenAI
        openai.api_key = self.config['openai_api_key']
        
        # RabbitMQ connection
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='user_input')
        self.channel.queue_declare(queue='system_output')
        
        # Message history
        self.conversation_history = []
        
        # System parameters
        self.max_message_num_in_context = self.config['dialogue']['max_message_num_in_context']
        self.max_tokens = self.config['dialogue']['max_tokens']
        self.model = self.config['dialogue']['response_generation_model']
        
    def generate_response(self, user_message):
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Prepare context
        context = self.conversation_history[-self.max_message_num_in_context:]
        
        try:
            # Generate response using OpenAI
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.config['dialogue']['system_prompt']},
                    *context
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            # Extract and store response
            system_message = response.choices[0].message['content']
            self.conversation_history.append({"role": "assistant", "content": system_message})
            
            return system_message
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, but I encountered an error. Could you please try again?"

    def process_message(self, ch, method, properties, body):
        # Decode message
        user_message = json.loads(body.decode())['message']
        
        # Generate response
        system_response = self.generate_response(user_message)
        
        # Send response
        self.channel.basic_publish(
            exchange='',
            routing_key='system_output',
            body=json.dumps({'message': system_response})
        )

    def run(self):
        # Start consuming messages
        self.channel.basic_consume(
            queue='user_input',
            on_message_callback=self.process_message,
            auto_ack=True
        )
        
        print("Dialogue system is running. Waiting for messages...")
        self.channel.start_consuming()

if __name__ == "__main__":
    dialogue_system = DialogueSystem()
    dialogue_system.run()
