"""
Spark Batch Layer - processes HDFS data and computes aggregated views
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as _sum, avg, desc, window, to_timestamp
from datetime import datetime
import sys


class BatchProcessor:
    """Batch layer processing using Spark"""
    
    def __init__(self, app_name: str = "RedditBatchProcessor"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
    
    def read_hdfs_data(self, hdfs_path: str, data_type: str):
        """
        Read data from HDFS
        
        Args:
            hdfs_path: Base HDFS path (e.g., hdfs://namenode:9000/data)
            data_type: Type of data (posts, comments, users)
        """
        path = f"{hdfs_path}/{data_type}/*/*/*/*/*/*.json"
        print(f"Reading data from {path}")
        
        df = self.spark.read.json(path)
        
        # Convert timestamp string to timestamp type
        if 'timestamp' in df.columns:
            df = df.withColumn('timestamp', to_timestamp(col('timestamp')))
        elif 'created_utc' in df.columns:
            df = df.withColumn('timestamp', to_timestamp(col('created_utc')))
        
        return df
    
    def compute_top_posts_per_subreddit(self, posts_df, output_path: str, date_filter: str = None):
        """
        Compute top-k posts per subreddit per day
        
        Args:
            posts_df: Posts DataFrame
            output_path: Output path for results
            date_filter: Optional date filter (YYYY-MM-DD)
        """
        print("Computing top posts per subreddit...")
        
        if date_filter:
            posts_df = posts_df.filter(col('timestamp').cast('date') == date_filter)
        
        # Add date column
        posts_df = posts_df.withColumn('date', col('timestamp').cast('date'))
        
        # Compute top posts
        top_posts = posts_df.groupBy('subreddit', 'date', 'post_id', 'title', 'user_id') \
            .agg(
                _sum('score').alias('total_score'),
                _sum('num_comments').alias('total_comments')
            ) \
            .orderBy(col('date').desc(), col('subreddit'), col('total_score').desc())
        
        # Save results
        top_posts.write.mode('overwrite').json(f"{output_path}/top_posts")
        
        print(f"Top posts saved to {output_path}/top_posts")
        return top_posts
    
    def compute_user_activity(self, posts_df, comments_df, output_path: str):
        """
        Compute user activity metrics
        
        Args:
            posts_df: Posts DataFrame
            comments_df: Comments DataFrame
            output_path: Output path for results
        """
        print("Computing user activity...")
        
        # Posts per user
        posts_per_user = posts_df.groupBy('user_id') \
            .agg(
                count('post_id').alias('num_posts'),
                _sum('score').alias('post_score')
            )
        
        # Comments per user
        comments_per_user = comments_df.groupBy('user_id') \
            .agg(
                count('comment_id').alias('num_comments'),
                _sum('score').alias('comment_score')
            )
        
        # Join and compute total activity
        user_activity = posts_per_user.join(comments_per_user, 'user_id', 'outer') \
            .fillna(0) \
            .withColumn('total_activity', col('num_posts') + col('num_comments')) \
            .withColumn('total_score', col('post_score') + col('comment_score')) \
            .orderBy(col('total_activity').desc())
        
        # Save results
        user_activity.write.mode('overwrite').json(f"{output_path}/user_activity")
        
        print(f"User activity saved to {output_path}/user_activity")
        return user_activity
    
    def compute_subreddit_activity(self, posts_df, comments_df, output_path: str):
        """
        Compute subreddit activity metrics
        
        Args:
            posts_df: Posts DataFrame
            comments_df: Comments DataFrame
            output_path: Output path for results
        """
        print("Computing subreddit activity...")
        
        # Add date column
        posts_df = posts_df.withColumn('date', col('timestamp').cast('date'))
        
        # Posts per subreddit per day
        subreddit_activity = posts_df.groupBy('subreddit', 'date') \
            .agg(
                count('post_id').alias('num_posts'),
                _sum('score').alias('total_score'),
                _sum('num_comments').alias('total_comments'),
                avg('score').alias('avg_score')
            ) \
            .orderBy(col('date').desc(), col('num_posts').desc())
        
        # Save results
        subreddit_activity.write.mode('overwrite').json(f"{output_path}/subreddit_activity")
        
        print(f"Subreddit activity saved to {output_path}/subreddit_activity")
        return subreddit_activity
    
    def run_batch_job(self, hdfs_path: str, output_path: str):
        """
        Run complete batch job
        
        Args:
            hdfs_path: HDFS input path
            output_path: Output path for results
        """
        print(f"Starting batch job - input: {hdfs_path}, output: {output_path}")
        
        # Read data
        posts_df = self.read_hdfs_data(hdfs_path, "posts")
        comments_df = self.read_hdfs_data(hdfs_path, "comments")
        users_df = self.read_hdfs_data(hdfs_path, "users")
        
        print(f"Loaded {posts_df.count()} posts, {comments_df.count()} comments, {users_df.count()} users")
        
        # Compute views
        self.compute_top_posts_per_subreddit(posts_df, output_path)
        self.compute_user_activity(posts_df, comments_df, output_path)
        self.compute_subreddit_activity(posts_df, comments_df, output_path)
        
        print("Batch job complete!")
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()


if __name__ == "__main__":
    hdfs_path = sys.argv[1] if len(sys.argv) > 1 else "hdfs://localhost:9000/data"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "hdfs://localhost:9000/output/batch"
    
    processor = BatchProcessor()
    try:
        processor.run_batch_job(hdfs_path, output_path)
    finally:
        processor.stop()
