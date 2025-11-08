"""
Integration tests for historical data generator
"""
import unittest
import os
import json
import tempfile
import shutil
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'data-generator'))

from historical_generator import HistoricalDataGenerator


class TestHistoricalGenerator(unittest.TestCase):
    """Test historical data generation"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = HistoricalDataGenerator(output_dir=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_generate_historical_data(self):
        """Test that historical data is generated correctly"""
        posts, comments, users = self.generator.generate_historical_data(
            num_days=2, 
            posts_per_day=10
        )
        
        # Check counts
        self.assertEqual(len(posts), 20)  # 2 days * 10 posts
        self.assertGreater(len(comments), 0)  # Some comments
        self.assertGreater(len(users), 0)  # Some users
    
    def test_data_files_created(self):
        """Test that JSON files are created"""
        self.generator.generate_historical_data(num_days=1, posts_per_day=5)
        
        # Check files exist
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "posts.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "comments.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "users.json")))
    
    def test_json_format(self):
        """Test that generated data is valid JSON"""
        self.generator.generate_historical_data(num_days=1, posts_per_day=5)
        
        # Read and parse posts
        posts_file = os.path.join(self.temp_dir, "posts.json")
        with open(posts_file, 'r') as f:
            for line in f:
                data = json.loads(line.strip())
                self.assertIn("post_id", data)
                self.assertIn("user_id", data)
                self.assertIn("subreddit", data)


if __name__ == "__main__":
    unittest.main()
