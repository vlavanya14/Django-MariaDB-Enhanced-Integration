"""
Custom Django fields for MariaDB advanced features
"""
from django.db import models
from django.core import exceptions
import json
import numpy as np


class VectorField(models.Field):
    """
    Store and query vector embeddings for semantic search
    Uses MariaDB's BLOB to store vectors as binary data
    """
    description = "Vector field for embeddings"
    
    def __init__(self, dimensions=None, *args, **kwargs):
        self.dimensions = dimensions
        kwargs['max_length'] = (dimensions * 8) if dimensions else 8192
        super().__init__(*args, **kwargs)
    
    def db_type(self, connection):
        """Use BLOB for binary vector storage"""
        return 'BLOB'
    
    def from_db_value(self, value, expression, connection):
        """Convert bytes back to numpy array"""
        if value is None:
            return value
        return np.frombuffer(value, dtype=np.float64)
    
    def to_python(self, value):
        """Convert to numpy array"""
        if isinstance(value, np.ndarray):
            return value
        if value is None:
            return value
        if isinstance(value, bytes):
            return np.frombuffer(value, dtype=np.float64)
        if isinstance(value, (list, tuple)):
            return np.array(value, dtype=np.float64)
        return value
    
    def get_prep_value(self, value):
        """Convert numpy array to bytes for storage"""
        if value is None:
            return value
        if isinstance(value, np.ndarray):
            return value.tobytes()
        if isinstance(value, (list, tuple)):
            return np.array(value, dtype=np.float64).tobytes()
        return value
    
    def value_to_string(self, obj):
        """Serialize for fixtures"""
        value = self.value_from_object(obj)
        return json.dumps(value.tolist()) if value is not None else None


class EnhancedJSONField(models.JSONField):
    """
    Enhanced JSON field with MariaDB JSON functions support
    Provides better indexing and query capabilities
    """
    
    def db_type(self, connection):
        return 'LONGTEXT'  # MariaDB supports JSON validation on TEXT fields
    
    def get_prep_value(self, value):
        """Ensure valid JSON"""
        if value is None:
            return value
        return json.dumps(value, ensure_ascii=False)


class TemporalMixin(models.Model):
    """
    Mixin for temporal table support (system-versioned tables)
    Tracks all historical changes automatically
    """
    # MariaDB will add these automatically when table is created as system-versioned
    # row_start = models.DateTimeField(editable=False)
    # row_end = models.DateTimeField(editable=False)
    
    class Meta:
        abstract = True
    
    @classmethod
    def enable_temporal(cls):
        """
        Enable system versioning on this model's table
        Call after migrations are complete
        """
        from django.db import connection
        table_name = cls._meta.db_table
        with connection.cursor() as cursor:
            # Check server version to ensure temporal/system-versioned tables
            # are supported (MariaDB >= 10.3). If not, raise a clear error so
            # callers can decide whether to continue.
            try:
                cursor.execute("SELECT VERSION()")
                server_version = cursor.fetchone()[0]
            except Exception:
                server_version = 'unknown'

            ver_str = str(server_version).lower()
            if 'mariadb' in ver_str:
                # Parse leading numeric version like '10.6.12-mariadb'
                numeric = ver_str.split('-')[0]
                parts = numeric.split('.')
                try:
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                except Exception:
                    major, minor = 0, 0

                if (major, minor) < (10, 3):
                    raise RuntimeError(f"Temporal tables require MariaDB >= 10.3; server version: {server_version}")
            else:
                # Not MariaDB (likely MySQL) — system-versioned syntax differs
                raise RuntimeError(f"Temporal/system-versioned tables not supported on this server: {server_version}")

            # Add system versioning columns and enable
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN row_start TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
                ADD COLUMN row_end TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
                ADD PERIOD FOR SYSTEM_TIME(row_start, row_end),
                ADD SYSTEM VERSIONING;
            """)
    
    @classmethod
    def get_history(cls, pk, start_date=None, end_date=None):
        """
        Get historical versions of a record
        """
        from django.db import connection
        table_name = cls._meta.db_table
        
        query = f"SELECT * FROM {table_name} FOR SYSTEM_TIME ALL WHERE id = %s"
        params = [pk]
        
        if start_date:
            query += " AND row_start >= %s"
            params.append(start_date)
        if end_date:
            query += " AND row_end <= %s"
            params.append(end_date)
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


class VectorQueryMixin:
    """
    Mixin to add vector similarity search to models with VectorField
    """
    
    @classmethod
    def search_similar(cls, vector, limit=10, threshold=0.7):
        """
        Find records with similar vectors using cosine similarity
        
        Args:
            vector: numpy array or list to compare against
            limit: maximum number of results
            threshold: minimum similarity score (0-1)
        
        Returns:
            QuerySet ordered by similarity score
        """
        from django.db.models import F, FloatField
        from django.db.models.functions import Cast
        from django.db import connection
        
        if isinstance(vector, (list, tuple)):
            vector = np.array(vector, dtype=np.float64)
        
        # For now, we'll fetch all and compute similarity in Python
        # In production, this would use a custom SQL function
        all_records = list(cls.objects.all())
        
        results = []
        for record in all_records:
            record_vector = getattr(record, cls._get_vector_field_name())
            if record_vector is not None:
                similarity = cls._cosine_similarity(vector, record_vector)
                if similarity >= threshold:
                    record.similarity_score = similarity
                    results.append(record)
        
        # Sort by similarity
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]
    
    @classmethod
    def _get_vector_field_name(cls):
        """Find the VectorField in this model"""
        for field in cls._meta.fields:
            if isinstance(field, VectorField):
                return field.name
        raise ValueError(f"No VectorField found in {cls.__name__}")
    
    @staticmethod
    def _cosine_similarity(vec1, vec2):
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if norm1 and norm2 else 0.0


class JSONQueryMixin:
    """
    Mixin for enhanced JSON querying capabilities
    """
    
    @classmethod
    def json_contains(cls, field_name, key, value):
        """
        Query records where JSON field contains a specific key-value pair
        """
        from django.db.models import Q
        lookup = f"{field_name}__{key}"
        return cls.objects.filter(**{lookup: value})
    
    @classmethod
    def json_extract(cls, field_name, path):
        """
        Extract values from JSON field at given path
        """
        from django.db import connection
        from django.db.models import F, Func
        
        # Use MariaDB's JSON_EXTRACT function
        return cls.objects.annotate(
            extracted_value=Func(
                F(field_name),
                Value(f'$.{path}'),
                function='JSON_EXTRACT',
                output_field=models.CharField()
            )
        )