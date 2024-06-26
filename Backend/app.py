import json
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, current_user
from psycopg2 import sql
import psycopg2
import csv
import io
import random
import string
from tempfile import SpooledTemporaryFile
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key

CORS(app)

login_manager = LoginManager(app)

login_manager.init_app(app)

def get_db_connection(database_name):
    """ Retrieves a database connection based on the city name and checks for overflows """
    base_db_name = database_name
    if(database_name == "cities"):
        db_name = "cities"
    elif get_schema_count(base_db_name) >= 4:
        db_name = check_and_create_overflow_db(base_db_name)
    else:
        db_name = base_db_name
    
    conn = psycopg2.connect(database=db_name, user="postgres", password="toor", host="localhost")
    return conn

def find_db_connection_from_city(city_name):
    """ Retrieves a database connection based on the city name by checking the cities database for the corresponding database entry """
    conn = psycopg2.connect(database="cities", user="postgres", password="toor", host="localhost")
    cursor = conn.cursor()
    try:
        # Assuming there's a table 'city_info' with columns 'city_name' and 'db_name'
        cursor.execute("SELECT db_name FROM city_info WHERE city_name = %s", (city_name,))
        result = cursor.fetchone()
        print(city_name, result)
        if result:
            db_name = result[0]
            return psycopg2.connect(database=db_name, user="postgres", password="toor", host="localhost")
        else:
            raise Exception(f"No database entry found for city: {city_name}")
    finally:
        cursor.close()
        conn.close()

# A simple user model (you may need to replace this with your database model)
class User(UserMixin):
    def __init__(self, id, name, email, password):
        self.id = id
        self.name = name
        self.email = email
        self.password = password

    def get_id(self):
        return self.id

# Dummy user (you should implement user lookup in your database)
users = [User(id=1, name='Genevieve', email='test@example.com', password='test123'), User(id=12345, name = 'shalin',email='shalinbh@usc.edu', password='test123'), User(id=123465, name = 'Admin',email='admin@usc.edu', password='admin123')]

# User loader
@login_manager.user_loader
def load_user(user_id):
    for user in users:
        if user.id == int(user_id):
            return user
    return None

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = next((u for u in users if u.email == email and u.password == password), None)
    if user:
        login_user(user)
        return jsonify({'success': True, 'message': 'Logged in successfully!', 'name': user.name}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials!'}), 401

    
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    fullname = data.get('name')
    email = data.get('email')
    password = data.get('password')

    hashed_password = password

    new_user = User(id=len(users)+1, name=fullname, email=email, password=hashed_password)
    users.append(new_user)

    return jsonify({'success': True, 'message': 'Registered successfully!', 'name': fullname}), 201

@app.route('/search', methods=['GET'])
def search_listing():
    query_params = request.args

    data = {key: query_params.getlist(key) if len(query_params.getlist(key)) > 1 else query_params[key] for key in query_params}

    print(data)
    city = data.get('city').lower().replace(' ', '_').replace('-', '_')

    amenities_list = ['Kitchen', 'Iron', 'Wifi', 'Parking','Gym','Pool','Washer','Dryer','Heating','Air conditioning','TV','Cable TV','Elevator','Family/kid friendly','Smoke detector','Carbon monoxide detector','First aid kit','Fire extinguisher','Essentials','Shampoo','Hangers','Hair dryer','Laptop friendly workspace','Private entrance','Hot water']

    sql = f"SELECT * FROM {city}.listings WHERE price >= {data['priceMin']} AND price <= {data['priceMax']} and name like '%{data['name']}%'"

    if data['bedrooms'] != '' and data['bedrooms'] != 'null':
        sql += f" AND beds = {data['bedrooms']}"

    if data['people'] != '' and data['people'] != 'null':
        sql += f" AND accommodates = {data['people']}"

    if data['rating'] != '' and data['rating'] != 'null':
        sql += f" AND review_scores_rating >= {data['rating']}"

    if 'amenities' in data and data['amenities'] != '' and data['amenities'] != 'null':
        if(isinstance(data['amenities'], str)):
            print(data['amenities'])
            sql+= f" AND amenities LIKE '%{data['amenities']}%' "
        else:
            # Iterate over each element in the amenities list
            for element in data['amenities']:
                # Add the LIKE condition for the current element to the SQL query
                sql += f" AND amenities LIKE '%{element}%' "

    print(sql)
    conn = find_db_connection_from_city(data.get('city'))
    cursor = conn.cursor() 
    cursor.execute(sql)
    rows = cursor.fetchall()

    # Transform the result into a list of dictionaries
    res = []
    columns = ['id', 'name', 'neighbourhood_cleansed', 'property_type', 'accommodates', 'bathrooms_text', 'beds', 'amenities', 'price', 'review_scores_rating']
    for row in rows:
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        row_dict['city'] = data['city']  # Add the city to each row's dictionary
        res.append(row_dict)

    return jsonify(res)

@app.route('/getReviews', methods=['GET'])
def get_Reviews():
    data = request.args
    listing_id = data.get('listing_id')
    city = data.get('city').lower().replace(' ', '_').replace('-', '_')
    # db_name = city[0]
    conn = find_db_connection_from_city(data.get('city'))
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT * FROM {city}.reviews
    INNER JOIN {city}.listings_reviews ON {city}.reviews.id = {city}.listings_reviews.review_id
    WHERE {city}.listings_reviews.listing_id = %s OR {city}.listings_reviews.listing_id = %s
    """, (f"{listing_id}.0", str(listing_id)))
    rows = cursor.fetchall()
    res = []
    columns = ['id', 'reviewer_id', 'reviewer_name', 'comments']
    for row in rows:
        res.append({columns[i]: row[i] for i in range(len(columns))})
    return jsonify(res)


@app.route('/getCitites', methods=['GET'])
def get_cities():
    conn = get_db_connection("cities")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT city_name FROM city_info")
        rows = cursor.fetchall()
        cities = [row[0] for row in rows]
    except Exception as e:
        print(f"Database query failed: {e}")
        cities = []
    finally:
        cursor.close()
        conn.close()
    return jsonify(cities)

@app.route('/insert', methods=['POST'])
def insert_property():
    data = request.get_json()
    city = data.get('city').lower().replace(' ', '_').replace('-', '_')
    conn = get_db_connection("cities")

    try:
        # Ensure the city exists in city_info and get db_name
        if city.lower() == "other":
            temp_city = data['otherCity']
            db_name = create_city_database(conn, temp_city)
            conn.close()  
            city = temp_city.lower().replace(' ', '_').replace('-', '_')
            conn = find_db_connection_from_city(temp_city)
        else:
            db_name = city[0]
            conn = find_db_connection_from_city(data.get('city'))

        print("in here")
        insert_property_data(data, conn, city)

        return jsonify({'success': True, 'message': 'Property inserted successfully!'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/deleteReview', methods=['POST'])
def delete_review():
    data = request.get_json()
    review_id = data.get('review_id')
    city = data.get('city').lower().replace(' ', '_').replace('-', '_')

    if not review_id:
        return jsonify({'success': False, 'message': 'Failure'}), 400

    # db_name = city[0]
    conn = find_db_connection_from_city(data.get('city'))

    try:
        with conn.cursor() as cur:
            # Delete from listings_reviews first to maintain referential integrity
            cur.execute(f"DELETE FROM {city}.listings_reviews WHERE review_id = %s", (review_id,))
            # Delete from reviews
            cur.execute(f"DELETE FROM {city}.reviews WHERE id = %s", (review_id,))

            conn.commit()  # Ensure changes are committed to the database

            return jsonify({'success': True, 'message': 'Review deleted successfully!'}), 200
    except Exception as e:
        conn.rollback()  # Rollback the transaction on error
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/updateReview/<review_id>', methods=['PUT'])
def update_review(review_id):
    data = request.get_json()
    city = data['city'].lower().replace(' ', '_').replace('-', '_')  # Use city in your database queries if needed
    # db_name = city[0]  # For database selection
    conn = find_db_connection_from_city(data['city'])
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE {city}.reviews SET comments = %s WHERE id = %s
            """, (data['comments'], review_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Review updated successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/addReview', methods=['POST'])
def add_review():
    data = request.get_json()
    city = data['city'].lower().replace(' ', '_').replace('-', '_')  # Use city in your database queries if needed
    # db_name = city[0]  # For database selection
    conn = find_db_connection_from_city(data['city'])
    
    # Generate unique IDs for the new review and listing_review entries
    new_review_id = str(my_random(5))  # or use your own function
    new_reviewer_id = str(my_random(5))

    try:
        with conn.cursor() as cur:
            # Insert into reviews table
            cur.execute(f"""
                INSERT INTO {city}.reviews (id, reviewer_id, reviewer_name, comments)
                VALUES (%s, %s, %s, %s)
            """, (new_review_id, new_reviewer_id, data['reviewer_name'], data['comments']))
            
            # Insert into listings_reviews linking table
            cur.execute(f"""
                INSERT INTO {city}.listings_reviews (listing_id, review_id)
                VALUES (%s, %s)
            """, (data['listing_id'], new_review_id))
            conn.commit()
            
            return jsonify({'success': True, 'message': 'New review added successfully', 'review_id': new_review_id, 'reviewer_id': new_reviewer_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

def get_schema_count(db_name):
    """ Utility function to get the count of schemas in a specific database """
    conn = psycopg2.connect(database=db_name, user="postgres", password="toor", host="localhost")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(schema_name) FROM information_schema.schemata
        WHERE catalog_name = %s AND schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast')
    """, (db_name,))
    count = cursor.fetchone()[0]
    print(f"Schema count for {db_name}: {count}")
    cursor.close()
    conn.close()
    return count

def check_and_create_overflow_db(base_db_name):
    """ Checks for overflow databases and creates a new one if necessary """
    overflow_db_name = f"{base_db_name}_overflow"
    if not database_exists(overflow_db_name):
        create_database(overflow_db_name)
    return overflow_db_name

def database_exists(db_name):
    """ Checks if a database exists """
    conn = psycopg2.connect(database="postgres", user="postgres", password="toor", host="localhost")
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def create_database(db_name):
    """ Creates a new database """
    conn = psycopg2.connect(database="postgres", user="postgres", password="toor", host="localhost")
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {db_name}")
    cursor.close()
    conn.close()
    print(f"Database {db_name} created successfully.")

def create_city_database(conn, city):
    base_db_name = city.lower().replace(' ', '_').replace('-', '_')[0]  # Assumes databases are named after the first letter of the city
    print(f"Creating database for {city} with base name {base_db_name}")
    
    if get_schema_count(base_db_name) >= 4:
        db_name = check_and_create_overflow_db(base_db_name)
    else:
        db_name = base_db_name
    print(f"Creating database for {city} with name {db_name}")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO city_info (city_name, db_name) VALUES (%s, %s) ON CONFLICT (city_name) DO NOTHING", (city, db_name))
        conn.commit()
    create_new_city_database(db_name, city)
    return db_name

def create_new_city_database(db_name, city):
    conn1 = psycopg2.connect(database="postgres", user="postgres", password="toor", host="localhost")
    conn1.autocommit = True
    cursor = conn1.cursor()
    try:
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        if cursor.fetchone() is None:
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database {db_name} created successfully.")
        else:
            print(f"Database {db_name} already exists.")
    except Exception as e:
        print(f"Failed to create database {db_name}: {e}")
    finally:
        cursor.close()
        conn1.close()

    # Connect to the new database and set up schema
    conn = find_db_connection_from_city(city)
    create_schema_if_not_exists(city, conn)
    setup_schema(conn, city)
    conn.close()

def create_schema_if_not_exists(schema_name, connection):
    city_schema = schema_name.lower().replace(' ', '_').replace('-', '_')
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {city_schema}")
            connection.commit()
            print(f"Schema {city_schema} created or already exists.")
    except psycopg2.Error as e:
        print(f"Failed to create or check schema {city_schema}: {e.pgerror}")
        connection.rollback()

def setup_schema(conn, city):
    city_schema = city.lower().replace(' ', '_').replace('-', '_')
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {city_schema}.listings (
                id TEXT PRIMARY KEY,
                name TEXT,
                neighbourhood_cleansed VARCHAR(255),
                property_type VARCHAR(255), 
                accommodates INT, 
                bathrooms_text VARCHAR(255), 
                beds FLOAT, 
                amenities TEXT, 
                price FLOAT, 
                review_scores_rating FLOAT
            );
            CREATE TABLE IF NOT EXISTS {city_schema}.reviews (
                id TEXT PRIMARY KEY,
                reviewer_id TEXT,
                reviewer_name TEXT,
                comments TEXT
            );
            CREATE TABLE IF NOT EXISTS {city_schema}.listings_reviews (
                listing_id TEXT,
                review_id TEXT,
                PRIMARY KEY (listing_id, review_id)
            );
        """)
        conn.commit()

def my_random(d):
    ''' Generates a random number with d digits '''
    return random.randint(int('1'+'0'*(d-1)), int('9'*d))

def insert_property_data(data, conn, city):
    city_schema = city.lower().replace(' ', '_').replace('-', '_')
    # Generate unique IDs for listing and review
    listing_id = str(my_random(5))
    id = str(my_random(5))
    review_id = str(my_random(5))
    print(listing_id,review_id)

    # Convert the comma-separated string into a list
    amenities_list = data['amenities'].split(',')

    # Now convert the list into a JSON string
    amenities_json = json.dumps([amenity.strip() for amenity in amenities_list])

    with conn.cursor() as cur:
        # Insert into listings
        
        cur.execute(f"""
            INSERT INTO {city}.listings (id, name, neighbourhood_cleansed, property_type, accommodates, bathrooms_text, beds, amenities, price, review_scores_rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            listing_id,
            data['name'],
            data['location'],  
            data['propertyType'],
            str(data['guests']),  # Assuming guests maps to accommodates
            str(data['bathrooms'])+" baths",  # Defaulting beds to 1 if not provided
            str(data['bedrooms']),
            amenities_json,
            float(data['price']),
            float(data['rating'])  # Assuming rating maps to review_scores_rating
        ))
        # print("Listings data inserted successfully.")
        # Insert into reviews
        cur.execute(f"""
            INSERT INTO {city_schema}.reviews (id, reviewer_id, reviewer_name, comments)
            VALUES (%s, %s, %s, %s)
        """, (
            id,
            review_id,
            str(data['reviewer_name']),  # Placeholder if not provided
            data['review']
        ))

        # Insert into listings_reviews linking table
        cur.execute(f"""
            INSERT INTO {city_schema}.listings_reviews (listing_id, review_id)
            VALUES (%s, %s)
        """, (listing_id, id))

        conn.commit()

def insert_data(cursor, listing_id, city, comment):
    review_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    try:
        cursor.execute(f"INSERT INTO {city.lower().replace(' ', '_').replace('-', '_')}.reviews VALUES (%s, 0000, 'admin', %s)", (review_id, comment))
        cursor.execute(f"INSERT INTO {city.lower().replace(' ', '_').replace('-', '_')}.listings_reviews VALUES (%s, %s)", (listing_id,review_id))
    except psycopg2.Error as e:
        print(f"Error inserting data: {e}")

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    file = request.files['file']
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    data_stream = io.StringIO(file.read().decode('utf-8-sig'))
    csv_reader = csv.DictReader(data_stream)

    grouped_data = {}
    for row in csv_reader:
        city = row['City'].strip()
        if city not in grouped_data:
            grouped_data[city] = []
        grouped_data[city].append(row)
    print(grouped_data)

    for city, records in grouped_data.items():
        print(city)
        conn = find_db_connection_from_city(city)
        if conn:
            with conn.cursor() as cursor:
                for record in records:
                    insert_data(cursor, record['Listing_id'], city, record['Comment'])
                conn.commit()
            conn.close()

    return jsonify({'message': 'File uploaded and processed successfully!'}), 200

@app.route('/removeAllReviews', methods=['GET'])
def removeReviews():
    listing_id = request.args.get('listing_id')
    city = request.args.get('city').lower().replace(' ', '_').replace('-', '_')
    # db_name = city[0]
    conn = find_db_connection_from_city(request.args.get('city'))
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {city}.reviews WHERE id IN (SELECT review_id FROM {city}.listings_reviews WHERE listing_id = %s OR listing_id = %s)", (f"{listing_id}", f"{listing_id}.0"))
            cur.execute(f"DELETE FROM {city}.listings_reviews WHERE listing_id = %s", (listing_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Reviews deleted successfully!'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(debug=True)
