"""
Spark Speed Layer - processes real-time data from Kafka
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as _sum, window, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
import sys


class SpeedProcessor:
    """Speed layer processing using Spark Structured Streaming"""
    
    def __init__(self, app_name: str = "RedditSpeedProcessor"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
    
    def get_post_schema(self):
        """Define schema for posts"""
        return StructType([
            StructField("post_id", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("subreddit", StringType(), True),
            StructField("title", StringType(), True),
            StructField("content", StringType(), True),
            StructField("score", IntegerType(), True),
            StructField("num_comments", IntegerType(), True),
            StructField("created_utc", StringType(), True),
            StructField("timestamp", StringType(), True)
        ])
    
    def get_comment_schema(self):
        """Define schema for comments"""
        return StructType([
            StructField("comment_id", StringType(), True),
            StructField("post_id", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("content", StringType(), True),
            StructField("score", IntegerType(), True),
            StructField("created_utc", StringType(), True),
            StructField("timestamp", StringType(), True)
        ])
    
    def get_user_schema(self):
        """Define schema for users"""
        return StructType([
            StructField("user_id", StringType(), True),
            StructField("username", StringType(), True),
            StructField("karma", IntegerType(), True),
            StructField("created_utc", StringType(), True),
            StructField("timestamp", StringType(), True)
        ])
    
    def read_kafka_stream(self, kafka_servers: str, topic: str, schema: StructType):
        """
        Read streaming data from Kafka
        
        Args:
            kafka_servers: Kafka bootstrap servers
            topic: Kafka topic
            schema: Schema for the data
        """
        print(f"Reading stream from Kafka topic: {topic}")
        
        df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", kafka_servers) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON value
        parsed_df = df.selectExpr("CAST(value AS STRING) as json") \
            .select(from_json(col("json"), schema).alias("data")) \
            .select("data.*")
        
        # Convert timestamp
        if 'timestamp' in parsed_df.columns:
            parsed_df = parsed_df.withColumn('timestamp', to_timestamp(col('timestamp')))
        
        return parsed_df
    
    def process_posts_stream(self, kafka_servers: str, elasticsearch_url: str):
        """
        Process posts stream and compute real-time metrics
        
        Args:
            kafka_servers: Kafka bootstrap servers
            elasticsearch_url: Elasticsearch URL
        """
        print("Processing posts stream...")
        
        posts_stream = self.read_kafka_stream(kafka_servers, "reddit.posts", self.get_post_schema())
        
        # Compute posts per minute per subreddit
        posts_per_minute = posts_stream \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "1 minute"),
                col("subreddit")
            ) \
            .agg(
                count("post_id").alias("num_posts"),
                _sum("score").alias("total_score")
            )
        
        # Write to Elasticsearch
        query = posts_per_minute.writeStream \
            .outputMode("update") \
            .format("org.elasticsearch.spark.sql") \
            .option("es.nodes", elasticsearch_url) \
            .option("es.port", "9200") \
            .option("es.resource", "views_subreddit_activity_v1") \
            .option("checkpointLocation", "/tmp/checkpoint/posts") \
            .start()
        
        return query
    
    def process_comments_stream(self, kafka_servers: str, elasticsearch_url: str):
        """
        Process comments stream
        
        Args:
            kafka_servers: Kafka bootstrap servers
            elasticsearch_url: Elasticsearch URL
        """
        print("Processing comments stream...")
        
        comments_stream = self.read_kafka_stream(kafka_servers, "reddit.comments", self.get_comment_schema())
        
        # Compute comments per minute
        comments_per_minute = comments_stream \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "1 minute"),
                col("post_id")
            ) \
            .agg(
                count("comment_id").alias("num_comments")
            )
        
        # Write to console for now (can be extended to write to Elasticsearch)
        query = comments_per_minute.writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .start()
        
        return query
    
    def process_user_stream(self, kafka_servers: str):
        """
        Process user updates stream
        
        Args:
            kafka_servers: Kafka bootstrap servers
        """
        print("Processing user stream...")
        
        users_stream = self.read_kafka_stream(kafka_servers, "reddit.users", self.get_user_schema())
        
        # Write to console
        query = users_stream.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .start()
        
        return query
    
    def run_streaming_job(self, kafka_servers: str, elasticsearch_url: str = "localhost"):
        """
        Run complete streaming job
        
        Args:
            kafka_servers: Kafka bootstrap servers
            elasticsearch_url: Elasticsearch URL
        """
        print(f"Starting streaming job - Kafka: {kafka_servers}, ES: {elasticsearch_url}")
        
        # Start all streams
        posts_query = self.process_posts_stream(kafka_servers, elasticsearch_url)
        # comments_query = self.process_comments_stream(kafka_servers, elasticsearch_url)
        # user_query = self.process_user_stream(kafka_servers)
        
        # Wait for termination
        posts_query.awaitTermination()
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()


if __name__ == "__main__":
    kafka_servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:9092"
    elasticsearch_url = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    
    processor = SpeedProcessor()
    try:
        processor.run_streaming_job(kafka_servers, elasticsearch_url)
    except KeyboardInterrupt:
        print("\nStopping streaming job...")
    finally:
        processor.stop()
