from app import db, User

# Replace 'username_here' with the actual username
user = User.query.filter_by(username='username_here').first()
if user:
    user.is_mod = True
    db.session.commit()
    print(f"{user.username} has been promoted to moderator.")
else:
    print("User not found.")