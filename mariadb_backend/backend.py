"""
Enhanced Django database backend for MariaDB
Extends django.db.backends.mysql with MariaDB-specific features
"""
from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as MySQLDatabaseFeatures
from django.db.backends.mysql.operations import DatabaseOperations as MySQLDatabaseOperations


class DatabaseFeatures(MySQLDatabaseFeatures):
    """
    Enhanced features for MariaDB
    """
    # MariaDB-specific feature flags
    supports_json_field = True
    supports_temporal_tables = True
    supports_vector_search = True
    has_json_operators = True
    supports_system_versioning = True
    
    # Inherited from MySQL but explicitly noted
    can_introspect_json_field = True
    supports_json_field_contains = True


class DatabaseOperations(MySQLDatabaseOperations):
    """
    Enhanced operations for MariaDB
    """
    
    def __init__(self, connection):
        super().__init__(connection)
        self.mariadb_version = None
    
    def get_mariadb_version(self):
        """Get MariaDB version tuple"""
        if self.mariadb_version is None:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version_string = cursor.fetchone()[0]
                # Parse version like "10.11.2-MariaDB"
                version_parts = version_string.split('-')[0].split('.')
                self.mariadb_version = tuple(int(x) for x in version_parts)
        return self.mariadb_version
    
    def check_mariadb_version(self, minimum=(10, 5, 0)):
        """Check if MariaDB version meets minimum requirement"""
        return self.get_mariadb_version() >= minimum
    
    def json_extract_sql(self, field_name, path):
        """
        Generate SQL for JSON field extraction
        MariaDB uses JSON_EXTRACT(field, '$.path')
        """
        return f"JSON_EXTRACT({field_name}, '$.{path}')"
    
    def json_contains_sql(self, field_name, value):
        """
        Generate SQL for JSON containment check
        MariaDB uses JSON_CONTAINS(field, value)
        """
        return f"JSON_CONTAINS({field_name}, JSON_QUOTE(%s))"
    
    def enable_temporal_table(self, table_name):
        """
        Enable system versioning (temporal tables) on a table
        """
        sql = f"""
            ALTER TABLE {table_name}
            ADD COLUMN IF NOT EXISTS row_start TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
            ADD COLUMN IF NOT EXISTS row_end TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
            ADD PERIOD FOR SYSTEM_TIME(row_start, row_end) IF NOT EXISTS,
            ADD SYSTEM VERSIONING IF NOT EXISTS;
        """
        return sql
    
    def temporal_query_sql(self, table_name, timestamp=None):
        """
        Generate SQL for temporal queries
        """
        if timestamp:
            return f"SELECT * FROM {table_name} FOR SYSTEM_TIME AS OF TIMESTAMP '{timestamp}'"
        else:
            return f"SELECT * FROM {table_name} FOR SYSTEM_TIME ALL"


class DatabaseWrapper(MySQLDatabaseWrapper):
    """
    Enhanced database wrapper for MariaDB
    """
    vendor = 'mariadb'
    display_name = 'MariaDB (Enhanced)'
    
    # Use our enhanced classes
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_mariadb = True
    
    def get_connection_params(self):
        """Enhanced connection parameters for MariaDB"""
        params = super().get_connection_params()
        
        # Add MariaDB-specific options
        options = params.get('OPTIONS', {})
        
        # Optimize for MariaDB
        options.setdefault('init_command', "SET sql_mode='STRICT_TRANS_TABLES'")
        options.setdefault('charset', 'utf8mb4')
        
        params['OPTIONS'] = options
        return params
    
    def init_connection_state(self):
        """Initialize connection with MariaDB-specific settings"""
        super().init_connection_state()
        
        # Verify we're connected to MariaDB
        with self.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            if 'MariaDB' not in version:
                raise Exception(
                    f"This backend requires MariaDB, but connected to: {version}"
                )
    
    def create_temporal_table(self, model):
        """
        Helper method to convert a model's table to temporal
        """
        table_name = model._meta.db_table
        with self.cursor() as cursor:
            sql = self.ops.enable_temporal_table(table_name)
            cursor.execute(sql)
            self.commit()