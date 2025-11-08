"""
Data consumer - bootstraps historical data and consumes from Kafka
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from kafka import KafkaConsumer
import hdfs
from hdfs import InsecureClient


class DataConsumer:
    """
    Consumer that:
    1. Bootstraps historical data to HDFS
    2. Consumes real-time data from Kafka and writes to HDFS
    """
    
    def __init__(self, 
                 kafka_servers: str = "localhost:9092",
                 hdfs_url: str = "http://localhost:9870",
                 hdfs_user: str = "hdfs"):
        self.kafka_servers = kafka_servers
        self.hdfs_url = hdfs_url
        self.hdfs_user = hdfs_user
        self.hdfs_client = None
        self.consumer = None
    
    def connect_hdfs(self):
        """Connect to HDFS"""
        try:
            self.hdfs_client = InsecureClient(self.hdfs_url, user=self.hdfs_user)
            # Test connection
            self.hdfs_client.list('/')
            print(f"Connected to HDFS at {self.hdfs_url}")
            return True
        except Exception as e:
            print(f"Failed to connect to HDFS: {e}")
            return False
    
    def bootstrap_historical_data(self, data_dir: str):
        """
        Load historical data from JSON files and write to HDFS
        
        Args:
            data_dir: Directory containing historical JSON files
        """
        print(f"Bootstrapping historical data from {data_dir}...")
        
        data_types = ["posts", "comments", "users"]
        
        for data_type in data_types:
            filepath = os.path.join(data_dir, f"{data_type}.json")
            if not os.path.exists(filepath):
                print(f"Warning: {filepath} not found, skipping")
                continue
            
            print(f"Processing {filepath}...")
            
            # Read and partition data by timestamp
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        self._write_to_hdfs(data_type, data)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                        continue
        
        print("Bootstrap complete!")
    
    def _write_to_hdfs(self, data_type: str, data: Dict[str, Any]):
        """
        Write data to HDFS partitioned by year/month/day/hour
        
        Args:
            data_type: Type of data (posts, comments, users)
            data: Data record to write
        """
        # Parse timestamp
        timestamp_str = data.get('timestamp') or data.get('created_utc')
        if not timestamp_str:
            print(f"Warning: No timestamp found in data: {data}")
            return
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            print(f"Warning: Invalid timestamp format: {timestamp_str}")
            return
        
        # Create partition path: /data/{type}/year={year}/month={month}/day={day}/hour={hour}/
        partition_path = f"/data/{data_type}/year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}/hour={timestamp.hour:02d}"
        
        # Create directory if it doesn't exist
        try:
            self.hdfs_client.makedirs(partition_path)
        except:
            pass  # Directory might already exist
        
        # Write data to file
        filename = f"{partition_path}/data_{timestamp.strftime('%Y%m%d%H%M%S%f')}.json"
        
        try:
            with self.hdfs_client.write(filename, encoding='utf-8') as writer:
                writer.write(json.dumps(data) + '\n')
        except Exception as e:
            print(f"Error writing to HDFS: {e}")
    
    def consume_from_kafka(self, topics: List[str]):
        """
        Consume messages from Kafka and write to HDFS
        
        Args:
            topics: List of Kafka topics to consume
        """
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.kafka_servers,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='hdfs-consumer-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            print(f"Connected to Kafka and subscribed to {topics}")
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            return
        
        print("Consuming messages from Kafka...")
        message_count = 0
        
        try:
            for message in self.consumer:
                data = message.value
                topic = message.topic
                
                # Extract data type from topic name
                data_type = topic.split('.')[-1]  # reddit.posts -> posts
                
                # Write to HDFS
                self._write_to_hdfs(data_type, data)
                
                message_count += 1
                if message_count % 100 == 0:
                    print(f"Consumed {message_count} messages")
        
        except KeyboardInterrupt:
            print("\nStopping consumer...")
        finally:
            if self.consumer:
                self.consumer.close()
            print(f"Total messages consumed: {message_count}")
    
    def run(self, historical_data_dir: str, kafka_topics: List[str]):
        """
        Run the full pipeline: bootstrap + streaming
        
        Args:
            historical_data_dir: Directory with historical JSON files
            kafka_topics: Kafka topics to consume
        """
        # Connect to HDFS
        if not self.connect_hdfs():
            print("Cannot proceed without HDFS connection")
            return
        
        # Bootstrap historical data
        if os.path.exists(historical_data_dir):
            self.bootstrap_historical_data(historical_data_dir)
        else:
            print(f"Warning: Historical data dir {historical_data_dir} not found, skipping bootstrap")
        
        # Start consuming from Kafka
        self.consume_from_kafka(kafka_topics)


if __name__ == "__main__":
    import sys
    
    kafka_servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:9092"
    hdfs_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:9870"
    historical_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp/historical_data"
    
    topics = ["reddit.posts", "reddit.comments", "reddit.users"]
    
    consumer = DataConsumer(kafka_servers=kafka_servers, hdfs_url=hdfs_url)
    consumer.run(historical_dir, topics)
