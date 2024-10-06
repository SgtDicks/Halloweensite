from app import db, User, Message

# List all tables
print(db.engine.table_names())

# Check if tables exist
user_exists = db.engine.dialect.has_table(db.engine, "user")
message_exists = db.engine.dialect.has_table(db.engine, "message")
print(f"User table exists: {user_exists}")
print(f"Message table exists: {message_exists}")
