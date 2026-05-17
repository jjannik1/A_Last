# utils.py

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Function to create a new user
async def create_user(username, email, name, surname1, surname2, location):
    # In a real application, this function would interact with a database
    return {
        "username": username,
        "email": email,
        "name": name,
        "surname1": surname1,
        "surname2": surname2,
        "location": location
    }

# Function to retrieve user profile information
async def get_user_profile(user_id):
    # In a real application, this function would query a database
    return {
        "_id": user_id,
        "username": "example_user",
        "email": "example@example.com",
        "name": "Example",
        "surname1": "User",
        "surname2": "",
        "location": "Example City"
    }

# Function to update user profile information
async def update_user_profile(user_id, new_data):
    # In a real application, this function would update a database
    return {
        "_id": user_id,
        "username": new_data.get("username", "example_user"),
        "email": new_data.get("email", "example@example.com"),
        "name": new_data.get("name", "Example"),
        "surname1": new_data.get("surname1", "User"),
        "surname2": new_data.get("surname2", ""),
        "location": new_data.get("location", "Example City")
    }

# Function to create a new post
async def create_post(user_id, text, visibility, media):
    # In a real application, this function would interact with a database
    return {
        "userId": user_id,
        "text": text,
        "images": media.get("images", []),
        "videos": media.get("videos", []),
        "visibility": visibility,
        "likes": [],
        "comments": [],
        "creacionDate": datetime.utcnow()
    }

# Function to retrieve all posts made by the given user
async def get_user_posts(user_id):
    # In a real application, this function would query a database
    return [
        {
            "_id": "5f9d1b9b9c9d6e0006045678",
            "userId": user_id,
            "text": "This is a sample post.",
            "images": ["/static/uploads/post_images/sample_image.jpg"],
            "videos": ["/static/uploads/post_videos/sample_video.mp4"],
            "visibility": "public",
            "likes": ["5f9d1b9b9c9d6e0006045679"],
            "comments": ["5f9d1b9b9c9d6e000604567a"],
            "creacionDate": datetime.utcnow()
        }
    ]

# Function to create a new comment
async def create_comment(post_id, user_id, text):
    # In a real application, this function would interact with a database
    return {
        "_id": "5f9d1b9b9c9d6e000604567b",
        "userId": user_id,
        "text": text,
        "creationDate": datetime.utcnow()
    }

# Function to like a post
async def like_post(post_id, user_id):
    # In a real application, this function would update a database
    return {
        "_id": post_id,
        "likes": [user_id]
    }

# Function to dislike a post
async def dislike_post(post_id, user_id):
    # In a real application, this function would update a database
    return {
        "_id": post_id,
        "likes": []
    }
