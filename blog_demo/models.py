from django.db import models
from django.utils import timezone
import json
import numpy as np


def _load_json_field(value):
    """Normalize a JSON-like field to a dict.

    Some DB drivers or custom fields return JSON as a string. This helper
    converts string JSON to Python objects and returns an empty dict for
    None/invalid values.
    """
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value


# Create your models here.
"""
Demo blog application showcasing MariaDB enhanced features
"""
from django.db import models
from django.contrib.auth.models import User
from mariadb_backend.fields import (
    VectorField, EnhancedJSONField, TemporalMixin,
    VectorQueryMixin, JSONQueryMixin
)


class Post(VectorQueryMixin, JSONQueryMixin, TemporalMixin):
    """
    Blog post with semantic search and metadata capabilities
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    
    # Vector field for semantic search
    content_vector = VectorField(
        dimensions=384,  # Sentence transformer dimension
        null=True,
        blank=True,
        help_text="Embedding vector for semantic search"
    )
    
    # Enhanced JSON field for flexible metadata
    metadata = models.JSONField(
        default=dict,
        help_text="Post metadata: tags, categories, SEO, etc."
    )
    
    # Standard fields
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    view_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['published', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Auto-generate vector embedding on save"""
        if self.content and (self.content_vector is None or len(self.content_vector) == 0):
            self.content_vector = self.generate_embedding()
        super().save(*args, **kwargs)
    
    def generate_embedding(self):
        """
        Generate vector embedding for content
        In production, this would use sentence-transformers
        For now, returns a dummy vector
        """
        import numpy as np
        # Placeholder: in real implementation, use:
        # from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # return model.encode(self.content)
        return np.random.rand(384)
    
    @classmethod
    def search_semantic(cls, query_text, limit=10):
        """
        Semantic search using vector similarity
        """
        # Generate embedding for query
        query_vector = np.random.rand(384)  # Placeholder
        return cls.search_similar(query_vector, limit=limit)
    
    def add_tag(self, tag):
        """Add tag to metadata"""
        metadata = _load_json_field(self.metadata)
        if 'tags' not in metadata:
            metadata['tags'] = []
        if tag not in metadata['tags']:
            metadata['tags'].append(tag)
            self.metadata = metadata
            self.save(update_fields=['metadata'])
    
    def set_category(self, category):
        """Set post category"""
        metadata = _load_json_field(self.metadata)
        metadata['category'] = category
        self.metadata = metadata
        self.save(update_fields=['metadata'])


class Comment(TemporalMixin):
    """
    Comments with audit trail via temporal tables
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    
    # Metadata for moderation, sentiment analysis, etc.
    metadata = models.JSONField(
        default=dict,
        help_text="Comment metadata: sentiment, flagged, edited, etc."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"
    
    def flag_for_moderation(self, reason):
        """Flag comment for moderation"""
        metadata = _load_json_field(self.metadata)
        metadata['flagged'] = True
        metadata['flag_reason'] = reason
        metadata['flagged_at'] = str(timezone.now())
        self.metadata = metadata
        self.is_approved = False
        self.save()


class UserProfile(models.Model):
    """
    Extended user profile with preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Vector for user interest/preference matching
    interest_vector = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="User interest vector for recommendations"
    )
    
    # JSON for flexible preferences
    preferences = EnhancedJSONField(
        default=dict,
        help_text="User preferences: theme, notifications, etc."
    )
    
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    
    def __str__(self):
        return f"Profile: {self.user.username}"
    
    def update_interests(self, posts_read):
        """
        Update user interest vector based on posts they've read
        """
        import numpy as np
        vectors = [p.content_vector for p in posts_read if p.content_vector is not None]
        if vectors:
            # Average of all post vectors
            self.interest_vector = np.mean(vectors, axis=0)
            self.save(update_fields=['interest_vector'])
    
    def get_recommendations(self, limit=10):
        """
        Get recommended posts based on user interests
        """
        if self.interest_vector is None:
            return Post.objects.filter(published=True)[:limit]
        
        return Post.search_similar(self.interest_vector, limit=limit)


class Analytics(models.Model):
    """
    Analytics data stored in JSON for flexible schema
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField(auto_now_add=True)
    
    # Store all metrics in JSON for flexibility
    metrics = models.JSONField(
        default=dict,
        help_text="Daily metrics: views, clicks, time_on_page, etc."
    )
    
    class Meta:
        unique_together = ['post', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.post.title} on {self.date}"
    
    def increment_metric(self, metric_name, amount=1):
        """Increment a metric value"""
        metrics = _load_json_field(self.metrics)
        if metric_name not in metrics:
            metrics[metric_name] = 0
        metrics[metric_name] += amount
        self.metrics = metrics
        self.save(update_fields=['metrics'])