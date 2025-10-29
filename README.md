# django-mariadb-enhanced

A demonstration project showcasing the integration of **Django** with **MariaDB** using advanced database features such as vector fields, JSON fields, and temporal tables.  
This prototype illustrates how modern applications can leverage MariaDB’s enhanced data capabilities for intelligent querying, similarity search, and recommendation systems.

---

## Features

- **Vector Field Search:**  
  Perform semantic or similarity-based searches using numeric vector fields.

- **JSON Query Support:**  
  Efficiently filter and query JSON fields using MariaDB JSON functions.

- **Temporal Tables:**  
  Track historical data changes automatically for audit and versioning use cases.

- **Recommendation System:**  
  Generate simple recommendations using stored vector data and user interactions.

---

## ⚙️ Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/<your-username>/django-mariadb-enhanced.git
   cd django-mariadb-enhanced


2. Create Virtual Environment
python -m venv venv
venv\Scripts\activate    # Windows
# or
source venv/bin/activate # macOS/Linux


3. Install Dependencies
pip install -r requirements.txt


4. Configure Database
Update settings.py with your MariaDB credentials:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'django_mariadb_demo',
        'USER': 'django_user',
        'PASSWORD': 'yourpassword',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}


5. Apply Migrations
python manage.py migrate


6. Create Demo Data
python manage.py create_demo_data


7. Run Server
python manage.py runserver


Visit: http://127.0.0.1:8000/

## Testing

Run all tests:
python manage.py test


Run a specific test:
python manage.py test blog_demo.tests.VectorFieldTestCase


Run with detailed output:
python manage.py test --verbosity=2


To interactively test in the Django shell:
python manage.py shell



Example commands:

from blog_demo.models import Post, UserProfile

posts = Post.objects.all()
if posts:
    query_vector = posts[0].content_vector
    similar = Post.search_similar(query_vector, limit=5)
    for post in similar:
        print(f"{post.title}: {post.similarity_score:.4f}")

print(f"Found {Post.json_contains('metadata', 'category', 'Tutorial').count()} tutorial posts")

user = UserProfile.objects.first()
if user:
    for post in user.get_recommendations(limit=5):
        print(post.title)



## Troublehooting

If mysqlclient fails to install:

Windows:

pip install wheel
pip install mysqlclient


macOS:

brew install mysql-client pkg-config
export PKG_CONFIG_PATH="$(brew --prefix)/opt/mysql-client/lib/pkgconfig"
pip install mysqlclient


Linux:

sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
pip install mysqlclient


If MariaDB won’t connect:

mysql -u root -p
# If fails:
# Windows: net start MySQL
# macOS: brew services start mariadb
# Linux: sudo systemctl start mariadb






## License

This project is for educational and demonstration purposes.
Modify and extend it as needed for your own Django + MariaDB integrations.