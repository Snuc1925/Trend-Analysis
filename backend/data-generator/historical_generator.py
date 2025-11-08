"""
Historical data generator for bootstrap load
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List
import random
from schemas import DataSchemas


class HistoricalDataGenerator:
    """Generate historical data for bootstrap load"""
    
    def __init__(self, output_dir: str = "/tmp/historical_data"):
        self.output_dir = output_dir
        self.schemas = DataSchemas()
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_historical_data(self, num_days: int = 7, posts_per_day: int = 1000):
        """
        Generate historical data for the past num_days
        
        Args:
            num_days: Number of days of historical data
            posts_per_day: Number of posts per day
        """
        print(f"Generating {num_days} days of historical data...")
        
        subreddits = ["python", "datascience", "machinelearning", "programming", "technology"]
        users = [f"user_{i}" for i in range(1000)]
        
        posts_data = []
        comments_data = []
        users_data = []
        
        # Generate users
        for user_id in users:
            user = self.schemas.generate_user(user_id, user_id)
            users_data.append(user)
        
        # Generate posts and comments for each day
        end_date = datetime.now(timezone.utc)
        for day_offset in range(num_days):
            date = end_date - timedelta(days=num_days - day_offset - 1)
            
            for i in range(posts_per_day):
                post_id = f"post_{date.strftime('%Y%m%d')}_{i}"
                user_id = random.choice(users)
                subreddit = random.choice(subreddits)
                
                post = self.schemas.generate_post(post_id, user_id, subreddit, date)
                posts_data.append(post)
                
                # Generate 0-10 comments per post
                num_comments = random.randint(0, 10)
                for j in range(num_comments):
                    comment_id = f"comment_{post_id}_{j}"
                    comment_user = random.choice(users)
                    comment = self.schemas.generate_comment(
                        comment_id, post_id, comment_user, 
                        date + timedelta(minutes=random.randint(1, 1440))
                    )
                    comments_data.append(comment)
        
        # Save to JSON files
        self._save_data("posts", posts_data)
        self._save_data("comments", comments_data)
        self._save_data("users", users_data)
        
        print(f"Generated {len(posts_data)} posts, {len(comments_data)} comments, {len(users_data)} users")
        return posts_data, comments_data, users_data
    
    def _save_data(self, data_type: str, data: List[dict]):
        """Save data to JSON file"""
        filepath = os.path.join(self.output_dir, f"{data_type}.json")
        with open(filepath, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        print(f"Saved {len(data)} {data_type} to {filepath}")


if __name__ == "__main__":
    generator = HistoricalDataGenerator()
    generator.generate_historical_data(num_days=7, posts_per_day=1000)
