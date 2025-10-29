from django.test import TestCase

# Create your tests here.
"""
Tests for MariaDB enhanced features
"""
from django.test import TestCase
from django.contrib.auth.models import User
from blog_demo.models import Post, Comment, UserProfile, Analytics
import numpy as np
from datetime import datetime, timedelta


class VectorFieldTestCase(TestCase):
    """Test vector field functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_vector_creation(self):
        """Test creating post with vector"""
        vector = np.random.rand(384)
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user,
            content_vector=vector
        )
        
        # Retrieve and verify
        post_db = Post.objects.get(pk=post.pk)
        self.assertIsNotNone(post_db.content_vector)
        self.assertEqual(len(post_db.content_vector), 384)
        np.testing.assert_array_almost_equal(post_db.content_vector, vector)
    
    def test_vector_similarity_search(self):
        """Test vector similarity search"""
        # Create posts with different vectors
        base_vector = np.random.rand(384)
        
        # Similar post
        similar_post = Post.objects.create(
            title='Similar Post',
            slug='similar-post',
            content='Similar content',
            author=self.user,
            content_vector=base_vector + np.random.rand(384) * 0.1  # Close to base
        )
        
        # Different post
        different_post = Post.objects.create(
            title='Different Post',
            slug='different-post',
            content='Different content',
            author=self.user,
            content_vector=np.random.rand(384)  # Random, likely different
        )
        
        # Search for similar
        results = Post.search_similar(base_vector, limit=10, threshold=0.5)
        
        # Should find at least one result
        self.assertGreater(len(results), 0)


class JSONFieldTestCase(TestCase):
    """Test enhanced JSON field functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_json_metadata(self):
        """Test JSON metadata storage and retrieval"""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user,
            metadata={
                'tags': ['django', 'mariadb', 'python'],
                'category': 'Tutorial',
                'reading_time': 5,
                'seo': {
                    'keywords': ['database', 'orm'],
                    'description': 'A test post'
                }
            }
        )
        
        # Retrieve and verify
        post_db = Post.objects.get(pk=post.pk)
        self.assertEqual(post_db.metadata['category'], 'Tutorial')
        self.assertEqual(len(post_db.metadata['tags']), 3)
        self.assertIn('django', post_db.metadata['tags'])
        self.assertEqual(post_db.metadata['seo']['keywords'], ['database', 'orm'])
    
    def test_json_query(self):
        """Test querying JSON fields"""
        # Create posts with different metadata
        Post.objects.create(
            title='Django Post',
            slug='django-post',
            content='About Django',
            author=self.user,
            metadata={'tags': ['django'], 'category': 'Tutorial'}
        )
        
        Post.objects.create(
            title='Python Post',
            slug='python-post',
            content='About Python',
            author=self.user,
            metadata={'tags': ['python'], 'category': 'Guide'}
        )
        
        # Query using JSON field
        django_posts = Post.objects.filter(metadata__category='Tutorial')
        self.assertEqual(django_posts.count(), 1)
        self.assertEqual(django_posts.first().title, 'Django Post')
    
    def test_json_update(self):
        """Test updating JSON fields"""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user,
            metadata={'tags': []}
        )
        
        # Add tag using helper method
        post.add_tag('django')
        post.add_tag('mariadb')
        
        post.refresh_from_db()
        self.assertIn('django', post.metadata['tags'])
        self.assertIn('mariadb', post.metadata['tags'])


class TemporalTableTestCase(TestCase):
    """Test temporal table functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_comment_creation(self):
        """Test creating comment (temporal table)"""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user
        )
        
        comment = Comment.objects.create(
            post=post,
            author=self.user,
            content='Test comment',
            metadata={'sentiment': 'positive'}
        )
        
        self.assertIsNotNone(comment.pk)
        self.assertEqual(comment.content, 'Test comment')
    
    def test_comment_moderation(self):
        """Test comment moderation workflow"""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user
        )
        
        comment = Comment.objects.create(
            post=post,
            author=self.user,
            content='Spam comment',
            is_approved=True
        )
        
        # Flag for moderation
        comment.flag_for_moderation('Potential spam')
        
        comment.refresh_from_db()
        self.assertFalse(comment.is_approved)
        self.assertTrue(comment.metadata['flagged'])
        self.assertEqual(comment.metadata['flag_reason'], 'Potential spam')


class UserProfileTestCase(TestCase):
    """Test user profile and recommendations"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.profile = UserProfile.objects.create(
            user=self.user,
            preferences={
                'theme': 'dark',
                'notifications': True
            }
        )
    
    def test_preference_storage(self):
        """Test storing user preferences"""
        self.assertEqual(self.profile.preferences['theme'], 'dark')
        self.assertTrue(self.profile.preferences['notifications'])
    
    def test_interest_vector(self):
        """Test user interest vector"""
        # Create posts
        posts = []
        for i in range(3):
            post = Post.objects.create(
                title=f'Post {i}',
                slug=f'post-{i}',
                content=f'Content {i}',
                author=self.user,
                content_vector=np.random.rand(384)
            )
            posts.append(post)
        
        # Update interests based on posts read
        self.profile.update_interests(posts)
        
        self.assertIsNotNone(self.profile.interest_vector)
        self.assertEqual(len(self.profile.interest_vector), 384)


class AnalyticsTestCase(TestCase):
    """Test analytics functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Test content',
            author=self.user
        )
    
    def test_analytics_creation(self):
        """Test creating analytics records"""
        analytics = Analytics.objects.create(
            post=self.post,
            metrics={
                'views': 100,
                'unique_visitors': 75,
                'avg_time_on_page': 120
            }
        )
        
        self.assertEqual(analytics.metrics['views'], 100)
        self.assertEqual(analytics.metrics['unique_visitors'], 75)
    
    def test_metric_increment(self):
        """Test incrementing metrics"""
        analytics = Analytics.objects.create(
            post=self.post,
            metrics={'views': 100}
        )
        
        # Increment views
        analytics.increment_metric('views', 10)
        
        analytics.refresh_from_db()
        self.assertEqual(analytics.metrics['views'], 110)


class PerformanceTestCase(TestCase):
    """Test performance improvements"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    def test_bulk_vector_operations(self):
        """Test bulk operations with vectors"""
        import time
        
        # Create 100 posts with vectors
        posts = []
        start_time = time.time()
        
        for i in range(100):
            posts.append(Post(
                title=f'Post {i}',
                slug=f'post-{i}',
                content=f'Content {i}',
                author=self.user,
                content_vector=np.random.rand(384)
            ))
        
        Post.objects.bulk_create(posts)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(duration, 5.0, f"Bulk create took {duration:.2f}s")
        self.assertEqual(Post.objects.count(), 100)
    
    def test_json_query_performance(self):
        """Test JSON query performance"""
        import time
        
        # Create posts with JSON metadata
        for i in range(50):
            Post.objects.create(
                title=f'Post {i}',
                slug=f'post-{i}',
                content=f'Content {i}',
                author=self.user,
                metadata={'category': 'Tutorial' if i % 2 == 0 else 'Guide'}
            )
        
        # Query using JSON field
        start_time = time.time()
        tutorial_posts = Post.objects.filter(metadata__category='Tutorial')
        count = tutorial_posts.count()
        end_time = time.time()
        
        duration = end_time - start_time
        
        self.assertEqual(count, 25)
        self.assertLess(duration, 1.0, f"JSON query took {duration:.2f}s")