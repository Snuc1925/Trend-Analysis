"""
Real-time data producer - sends data to Kafka
"""
import json
import time
from datetime import datetime
from typing import Optional
import random
from kafka import KafkaProducer
from schemas import DataSchemas


class RealtimeDataProducer:
    """Produces real-time data to Kafka topics"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.schemas = DataSchemas()
        self.subreddits = ["python", "datascience", "machinelearning", "programming", "technology"]
        self.users = [f"user_{i}" for i in range(1000)]
        self.post_counter = 0
        self.comment_counter = 0
    
    def connect(self):
        """Connect to Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_block_ms=5000
            )
            print(f"Connected to Kafka at {self.bootstrap_servers}")
            return True
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            return False
    
    def produce_post(self):
        """Produce a random post"""
        post_id = f"realtime_post_{self.post_counter}"
        user_id = random.choice(self.users)
        subreddit = random.choice(self.subreddits)
        
        post = self.schemas.generate_post(post_id, user_id, subreddit)
        
        self.producer.send('reddit.posts', value=post)
        self.post_counter += 1
        return post
    
    def produce_comment(self, post_id: Optional[str] = None):
        """Produce a random comment"""
        if post_id is None:
            post_id = f"realtime_post_{random.randint(0, max(0, self.post_counter-1))}"
        
        comment_id = f"realtime_comment_{self.comment_counter}"
        user_id = random.choice(self.users)
        
        comment = self.schemas.generate_comment(comment_id, post_id, user_id)
        
        self.producer.send('reddit.comments', value=comment)
        self.comment_counter += 1
        return comment
    
    def produce_user_update(self):
        """Produce a user update"""
        user_id = random.choice(self.users)
        user = self.schemas.generate_user(user_id, user_id)
        
        self.producer.send('reddit.users', value=user)
        return user
    
    def run(self, messages_per_second: int = 10, duration_seconds: Optional[int] = None):
        """
        Run the producer continuously
        
        Args:
            messages_per_second: Target throughput
            duration_seconds: How long to run (None = indefinitely)
        """
        if not self.producer:
            if not self.connect():
                print("Cannot start producer - connection failed")
                return
        
        print(f"Starting producer: {messages_per_second} msg/sec")
        start_time = time.time()
        message_count = 0
        
        try:
            while True:
                # Check duration
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break
                
                # Produce messages
                batch_start = time.time()
                for _ in range(messages_per_second):
                    # 70% posts, 25% comments, 5% user updates
                    rand = random.random()
                    if rand < 0.7:
                        self.produce_post()
                    elif rand < 0.95:
                        self.produce_comment()
                    else:
                        self.produce_user_update()
                    
                    message_count += 1
                
                # Sleep to maintain rate
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                
                # Print stats every 10 seconds
                if message_count % (messages_per_second * 10) == 0:
                    elapsed_total = time.time() - start_time
                    rate = message_count / elapsed_total if elapsed_total > 0 else 0
                    print(f"Produced {message_count} messages ({rate:.2f} msg/sec)")
        
        except KeyboardInterrupt:
            print("\nStopping producer...")
        finally:
            if self.producer:
                self.producer.flush()
                self.producer.close()
            
            total_time = time.time() - start_time
            print(f"Produced {message_count} messages in {total_time:.2f}s")
            print(f"Average rate: {message_count/total_time:.2f} msg/sec")


if __name__ == "__main__":
    import sys
    
    kafka_server = sys.argv[1] if len(sys.argv) > 1 else "localhost:9092"
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    producer = RealtimeDataProducer(bootstrap_servers=kafka_server)
    producer.run(messages_per_second=rate)
