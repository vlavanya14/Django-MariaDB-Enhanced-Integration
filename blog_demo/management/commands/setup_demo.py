"""
Management command to set up demo data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog_demo.models import Post, Comment, UserProfile, Analytics
import numpy as np
from datetime import datetime, timedelta
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Set up demo blog data with vectors and temporal tables'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--enable-temporal',
            action='store_true',
            help='Enable temporal tables for Post and Comment models',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up demo data...')
        
        # Create users
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin.set_password('admin123')
        admin.save()
        
        users = []
        for i in range(1, 6):
            user, _ = User.objects.get_or_create(
                username=f'user{i}',
                defaults={'email': f'user{i}@example.com'}
            )
            user.set_password('password123')
            user.save()
            users.append(user)
            
            # Create user profile
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'bio': f'Bio for user {i}',
                    'preferences': {
                        'theme': 'dark' if i % 2 == 0 else 'light',
                        'notifications': True,
                        'email_updates': i % 3 == 0
                    }
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(users) + 1} users'))
        
        # Sample blog posts
        post_data = [
            {
                'title': 'Getting Started with Django and MariaDB',
                'content': 'Django is a powerful web framework that works great with MariaDB. This post explores how to set up your first Django project with MariaDB as the database backend.',
                'metadata': {
                    'tags': ['django', 'mariadb', 'tutorial'],
                    'category': 'Tutorial',
                    'reading_time': 5,
                    'seo_keywords': ['django', 'mariadb', 'database']
                }
            },
            {
                'title': 'Vector Search in Modern Web Applications',
                'content': 'Vector search enables semantic similarity matching, allowing users to find content based on meaning rather than just keywords. Learn how to implement vector search in your Django application.',
                'metadata': {
                    'tags': ['vector-search', 'ai', 'semantic-search'],
                    'category': 'AI/ML',
                    'reading_time': 8,
                    'featured': True
                }
            },
            {
                'title': 'Temporal Tables: Track Every Change',
                'content': 'Temporal tables automatically track all changes to your data, providing a complete audit trail. This is essential for compliance, debugging, and understanding data evolution over time.',
                'metadata': {
                    'tags': ['temporal-tables', 'audit', 'mariadb'],
                    'category': 'Database',
                    'reading_time': 6
                }
            },
            {
                'title': 'JSON Fields vs Traditional Columns',
                'content': 'When should you use JSON fields instead of traditional columns? This post explores the trade-offs and best practices for flexible schema design in modern web applications.',
                'metadata': {
                    'tags': ['json', 'database-design', 'best-practices'],
                    'category': 'Database',
                    'reading_time': 7
                }
            },
            {
                'title': 'Building Recommendation Systems with Django',
                'content': 'Recommendation systems power modern web experiences. Learn how to build a content recommendation system using vector embeddings and similarity search in Django.',
                'metadata': {
                    'tags': ['recommendations', 'machine-learning', 'django'],
                    'category': 'AI/ML',
                    'reading_time': 10,
                    'featured': True
                }
            }
        ]
        
        posts = []
        for i, data in enumerate(post_data):
            post, created = Post.objects.get_or_create(
                slug=data['title'].lower().replace(' ', '-').replace(':', ''),
                defaults={
                    'title': data['title'],
                    'content': data['content'],
                    'author': users[i % len(users)],
                    'metadata': data['metadata'],
                    'published': True,
                    'view_count': np.random.randint(100, 1000),
                    'content_vector': np.random.rand(384)  # Placeholder vector
                }
            )
            posts.append(post)
            if created:
                self.stdout.write(f'  Created post: {post.title}')
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(posts)} posts'))
        
        # Create comments
        comment_texts = [
            "Great article! Very informative.",
            "Thanks for sharing this. It helped me a lot.",
            "I have a question about the implementation...",
            "This is exactly what I was looking for!",
            "Could you provide more examples?",
            "Excellent explanation of the concepts.",
        ]
        
        comments_created = 0
        for post in posts:
            for i in range(np.random.randint(2, 5)):
                comment, created = Comment.objects.get_or_create(
                    post=post,
                    author=users[i % len(users)],
                    content=comment_texts[i % len(comment_texts)],
                    defaults={
                        'metadata': {
                            'sentiment': np.random.choice(['positive', 'neutral']),
                            'edited': False
                        }
                    }
                )
                if created:
                    comments_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {comments_created} comments'))
        
        # Create analytics data
        analytics_created = 0
        for post in posts:
            for days_ago in range(7):
                date = datetime.now().date() - timedelta(days=days_ago)
                # Safer creation path: check for existence first and create only
                # if not present. This avoids the get_or_create race/duplicate
                # insert behavior on some MySQL backends in demo scripts.
                if not Analytics.objects.filter(post=post, date=date).exists():
                    try:
                        Analytics.objects.create(
                            post=post,
                            date=date,
                            metrics={
                                'views': np.random.randint(50, 200),
                                'unique_visitors': np.random.randint(30, 150),
                                'avg_time_on_page': np.random.randint(60, 300),
                                'bounce_rate': round(np.random.uniform(0.2, 0.6), 2),
                                'shares': np.random.randint(0, 20)
                            }
                        )
                        analytics_created += 1
                    except Exception as e:
                        # If a duplicate-key error still occurs, ignore and
                        # continue; otherwise re-raise.
                        if 'duplicate entry' in str(e).lower():
                            continue
                        raise
        
        self.stdout.write(self.style.SUCCESS(f'Created {analytics_created} analytics records'))
        
        # Enable temporal tables if requested
        if options['enable_temporal']:
            self.stdout.write('Enabling temporal tables...')
            try:
                Post.enable_temporal()
                Comment.enable_temporal()
                self.stdout.write(self.style.SUCCESS('Temporal tables enabled!'))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Could not enable temporal tables: {e}')
                )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Demo setup complete!'))
        self.stdout.write('\nYou can now:')
        self.stdout.write('  - Access admin at http://127.0.0.1:8000/admin/')
        self.stdout.write('  - Login with: admin / admin123')
        self.stdout.write('  - Test vector search and JSON queries')