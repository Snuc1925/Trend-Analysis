"""
Data schemas for Reddit-like data
"""
from datetime import datetime, timezone
from typing import Dict, Any
import random
import string


class DataSchemas:
    """Defines schemas for posts, comments, and users"""
    
    @staticmethod
    def generate_post(post_id: str, user_id: str, subreddit: str, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a post schema"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        return {
            "post_id": post_id,
            "user_id": user_id,
            "subreddit": subreddit,
            "title": f"Post title {post_id}",
            "content": f"Post content for {post_id}",
            "score": random.randint(0, 1000),
            "num_comments": random.randint(0, 100),
            "created_utc": timestamp.isoformat(),
            "timestamp": timestamp.isoformat()
        }
    
    @staticmethod
    def generate_comment(comment_id: str, post_id: str, user_id: str, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a comment schema"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        return {
            "comment_id": comment_id,
            "post_id": post_id,
            "user_id": user_id,
            "content": f"Comment content for {comment_id}",
            "score": random.randint(-10, 100),
            "created_utc": timestamp.isoformat(),
            "timestamp": timestamp.isoformat()
        }
    
    @staticmethod
    def generate_user(user_id: str, username: str, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a user schema"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        return {
            "user_id": user_id,
            "username": username,
            "karma": random.randint(0, 10000),
            "created_utc": timestamp.isoformat(),
            "timestamp": timestamp.isoformat()
        }
