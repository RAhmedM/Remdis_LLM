# simulator.py 
import pika
import json
import openai
import time
import yaml

class Simulator:
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
        
        # Conversation history
        self.conversation_history = []
        
        # Simulator parameters
        self.model = self.config['simulator']['model']
        self.max_turns = self.config['simulator']['max_turns']
        self.current_turn = 0

    def evaluate_conversation(self):
        evaluation_prompt = f"""
        Please evaluate the following dialogue based on these criteria:
        1. Fluency (1-5): Is the dialogue smooth and natural?
        2. Coherence (1-5): Is the content logically connected and consistent?
        3. Relevance (1-5): Are responses contextually appropriate?
        4. Informativeness (1-5): Does the dialogue provide valuable information?

        Dialogue:
        {self.format_conversation_history()}

        Provide scores and brief explanations for each criterion.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert dialogue system evaluator."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            return response.choices[0].message['content']
        except Exception as e:
            return f"Evaluation error: {e}"

    def format_conversation_history(self):
        formatted = ""
        for msg in self.conversation_history:
            role = "User" if msg['role'] == "user" else "System"
            formatted += f"{role}: {msg['content']}\n"
        return formatted

    def generate_user_message(self):
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.config['simulator']['user_prompt']},
                    *self.conversation_history[-4:]
                ],
                max_tokens=150,
                temperature=0.8
            )
            return response.choices[0].message['content']
        except Exception as e:
            print(f"Error generating user message: {e}")
            return None

    def process_system_response(self, ch, method, properties, body):
        # Decode and store system response
        system_message = json.loads(body.decode())['message']
        self.conversation_history.append({"role": "assistant", "content": system_message})
        
        # Increment turn counter
        self.current_turn += 1
        
        if self.current_turn < self.max_turns:
            # Generate and send next user message
            time.sleep(2)  # Add delay for more natural conversation flow
            user_message = self.generate_user_message()
            
            if user_message:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.channel.basic_publish(
                    exchange='',
                    routing_key='user_input',
                    body=json.dumps({'message': user_message})
                )
        else:
            # End conversation and evaluate
            print("\nConversation complete. Evaluating dialogue...")
            evaluation = self.evaluate_conversation()
            print("\nEvaluation Results:")
            print(evaluation)
            print("\nFinal dialogue:")
            print(self.format_conversation_history())
            
            # Save results
            results = {
                'dialogue': self.conversation_history,
                'evaluation': evaluation
            }
            with open(f'dialogue_evaluation_{time.strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            self.connection.close()
            exit(0)

    def start_conversation(self):
        initial_message = self.generate_user_message()
        if initial_message:
            self.conversation_history.append({"role": "user", "content": initial_message})
            self.channel.basic_publish(
                exchange='',
                routing_key='user_input',
                body=json.dumps({'message': initial_message})
            )

    def run(self):
        self.channel.basic_consume(
            queue='system_output',
            on_message_callback=self.process_system_response,
            auto_ack=True
        )
        
        self.start_conversation()
        
        print("Simulator is running. Starting conversation...")
        self.channel.start_consuming()

if __name__ == "__main__":
    simulator = Simulator()
    simulator.run()