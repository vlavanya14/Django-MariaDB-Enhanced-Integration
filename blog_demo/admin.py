from django.contrib import admin

# Register your models here.
"""
Django admin configuration for blog demo
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Post, Comment, UserProfile, Analytics


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'published', 'view_count', 'created_at', 'has_vector']
    list_filter = ['published', 'created_at', 'author']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'view_count', 'vector_info']
    
    fieldsets = [
        ('Content', {
            'fields': ['title', 'slug', 'content', 'author']
        }),
        ('Metadata', {
            'fields': ['metadata', 'published']
        }),
        ('Vector Search', {
            'fields': ['content_vector', 'vector_info'],
            'classes': ['collapse']
        }),
        ('Stats', {
            'fields': ['view_count', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def has_vector(self, obj):
        """Show if post has vector embedding"""
        if obj.content_vector is not None:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_vector.short_description = 'Vector'
    
    def vector_info(self, obj):
        """Display vector information"""
        if obj.content_vector is not None:
            import numpy as np
            vec = obj.content_vector
            return format_html(
                '<strong>Dimension:</strong> {}<br>'
                '<strong>Norm:</strong> {:.4f}<br>'
                '<strong>First 5 values:</strong> {}',
                len(vec),
                np.linalg.norm(vec),
                ', '.join(f'{v:.4f}' for v in vec[:5])
            )
        return 'No vector embedding'
    vector_info.short_description = 'Vector Information'
    
    actions = ['regenerate_vectors', 'mark_published']
    
    def regenerate_vectors(self, request, queryset):
        """Regenerate vector embeddings"""
        for post in queryset:
            post.content_vector = post.generate_embedding()
            post.save(update_fields=['content_vector'])
        self.message_user(request, f'Regenerated vectors for {queryset.count()} posts')
    regenerate_vectors.short_description = 'Regenerate vector embeddings'
    
    def mark_published(self, request, queryset):
        """Mark posts as published"""
        queryset.update(published=True)
        self.message_user(request, f'Marked {queryset.count()} posts as published')
    mark_published.short_description = 'Mark as published'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'is_approved', 'created_at', 'metadata_preview']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'author__username', 'post__title']
    readonly_fields = ['created_at', 'updated_at', 'metadata_display']
    
    fieldsets = [
        ('Comment', {
            'fields': ['post', 'author', 'content']
        }),
        ('Moderation', {
            'fields': ['is_approved', 'metadata']
        }),
        ('Metadata Details', {
            'fields': ['metadata_display'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def metadata_preview(self, obj):
        """Show preview of metadata"""
        if obj.metadata:
            items = list(obj.metadata.items())[:2]
            preview = ', '.join(f'{k}: {v}' for k, v in items)
            if len(obj.metadata) > 2:
                preview += '...'
            return preview
        return '-'
    metadata_preview.short_description = 'Metadata'
    
    def metadata_display(self, obj):
        """Display full metadata nicely"""
        import json
        if obj.metadata:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return 'No metadata'
    metadata_display.short_description = 'Full Metadata'
    
    actions = ['approve_comments', 'flag_for_review']
    
    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        queryset.update(is_approved=True)
        self.message_user(request, f'Approved {queryset.count()} comments')
    approve_comments.short_description = 'Approve comments'
    
    def flag_for_review(self, request, queryset):
        """Flag comments for review"""
        for comment in queryset:
            comment.flag_for_moderation('Admin review requested')
        self.message_user(request, f'Flagged {queryset.count()} comments for review')
    flag_for_review.short_description = 'Flag for review'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'has_interests', 'preference_count']
    search_fields = ['user__username', 'bio']
    readonly_fields = ['interest_info', 'preference_display']
    
    fieldsets = [
        ('User', {
            'fields': ['user', 'bio', 'avatar_url']
        }),
        ('Interests', {
            'fields': ['interest_vector', 'interest_info'],
            'classes': ['collapse']
        }),
        ('Preferences', {
            'fields': ['preferences', 'preference_display'],
            'classes': ['collapse']
        })
    ]
    
    def has_interests(self, obj):
        """Check if user has interest vector"""
        if obj.interest_vector is not None:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_interests.short_description = 'Has Interests'
    
    def preference_count(self, obj):
        """Count preferences"""
        return len(obj.preferences) if obj.preferences else 0
    preference_count.short_description = '# Preferences'
    
    def interest_info(self, obj):
        """Display interest vector info"""
        if obj.interest_vector is not None:
            import numpy as np
            vec = obj.interest_vector
            return format_html(
                '<strong>Dimension:</strong> {}<br>'
                '<strong>Norm:</strong> {:.4f}',
                len(vec),
                np.linalg.norm(vec)
            )
        return 'No interest vector'
    interest_info.short_description = 'Interest Vector'
    
    def preference_display(self, obj):
        """Display preferences nicely"""
        import json
        if obj.preferences:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
                json.dumps(obj.preferences, indent=2)
            )
        return 'No preferences set'
    preference_display.short_description = 'All Preferences'


@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = ['post', 'date', 'total_views', 'unique_visitors', 'avg_time']
    list_filter = ['date']
    search_fields = ['post__title']
    readonly_fields = ['metrics_display']
    date_hierarchy = 'date'
    
    fieldsets = [
        ('Analytics', {
            'fields': ['post', 'date', 'metrics']
        }),
        ('Metrics Details', {
            'fields': ['metrics_display'],
            'classes': ['collapse']
        })
    ]
    
    def total_views(self, obj):
        """Get total views from metrics"""
        return obj.metrics.get('views', 0)
    total_views.short_description = 'Views'
    
    def unique_visitors(self, obj):
        """Get unique visitors from metrics"""
        return obj.metrics.get('unique_visitors', 0)
    unique_visitors.short_description = 'Unique Visitors'
    
    def avg_time(self, obj):
        """Get average time on page"""
        seconds = obj.metrics.get('avg_time_on_page', 0)
        return f'{seconds // 60}m {seconds % 60}s'
    avg_time.short_description = 'Avg Time'
    
    def metrics_display(self, obj):
        """Display all metrics nicely"""
        import json
        if obj.metrics:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
                json.dumps(obj.metrics, indent=2)
            )
        return 'No metrics'
    metrics_display.short_description = 'All Metrics'