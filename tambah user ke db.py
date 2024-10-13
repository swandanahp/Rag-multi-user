import bcrypt
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/Testing"

# Set up engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Base model class
Base = declarative_base()

# Define User table
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)

# Create the table if it doesn't exist
Base.metadata.create_all(engine)

# Function to hash passwords
def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# Example function to populate the table
def populate_users():
    # Sample users with plain text passwords
    users = [
        {"username": "admin", "password": "admin123", "role": "admin"},
        {"username": "dika", "password": "user123", "role": "user"},
    ]
    
    for user_data in users:
        # Hash the password before storing it
        user_data['password_hash'] = hash_password(user_data.pop('password'))
        user = User(**user_data)
        session.add(user)
    
    # Commit the transaction
    session.commit()

# Call the function to populate the database
populate_users()

print("Database initialized and populated with hashed passwords.")
