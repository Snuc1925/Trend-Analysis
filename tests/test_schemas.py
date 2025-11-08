"""
Unit tests for data schemas
"""
import unittest
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'data-generator'))

from schemas import DataSchemas


class TestDataSchemas(unittest.TestCase):
    """Test data schema generation"""
    
    def setUp(self):
        self.schemas = DataSchemas()
    
    def test_generate_post(self):
        """Test post schema generation"""
        post = self.schemas.generate_post("post1", "user1", "python")
        
        self.assertEqual(post["post_id"], "post1")
        self.assertEqual(post["user_id"], "user1")
        self.assertEqual(post["subreddit"], "python")
        self.assertIn("title", post)
        self.assertIn("content", post)
        self.assertIn("score", post)
        self.assertIn("num_comments", post)
        self.assertIn("timestamp", post)
    
    def test_generate_comment(self):
        """Test comment schema generation"""
        comment = self.schemas.generate_comment("comment1", "post1", "user1")
        
        self.assertEqual(comment["comment_id"], "comment1")
        self.assertEqual(comment["post_id"], "post1")
        self.assertEqual(comment["user_id"], "user1")
        self.assertIn("content", comment)
        self.assertIn("score", comment)
        self.assertIn("timestamp", comment)
    
    def test_generate_user(self):
        """Test user schema generation"""
        user = self.schemas.generate_user("user1", "username1")
        
        self.assertEqual(user["user_id"], "user1")
        self.assertEqual(user["username"], "username1")
        self.assertIn("karma", user)
        self.assertIn("timestamp", user)
    
    def test_timestamp_format(self):
        """Test that timestamps are in ISO format"""
        timestamp = datetime.now(timezone.utc)
        post = self.schemas.generate_post("post1", "user1", "python", timestamp)
        
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(post["timestamp"])
        self.assertIsInstance(parsed, datetime)


if __name__ == "__main__":
    unittest.main()
