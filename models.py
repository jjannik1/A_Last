from datetime import datetime

class User:
    def __init__(self, user_id, username, email, name, surname1, surname2, location):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.name = name
        self.surname1 = surname1
        self.surname2 = surname2
        self.location = location

    def to_dict(self):
        return {
            "_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "surname1": self.surname1,
            "surname2": self.surname2,
            "location": self.location
        }

class Post:
    def __init__(self, post_id, user_id, text, visibility, images, videos, likes, comments, creacion_date):
        self.post_id = post_id
        self.user_id = user_id
        self.text = text
        self.visibility = visibility
        self.images = images
        self.videos = videos
        self.likes = likes
        self.comments = comments
        self.creacion_date = creacion_date

    def to_dict(self):
        return {
            "_id": self.post_id,
            "userId": self.user_id,
            "text": self.text,
            "visibility": self.visibility,
            "images": self.images,
            "videos": self.videos,
            "likes": self.likes,
            "comments": self.comments,
            "creacionDate": self.creacion_date.isoformat()
        }

class Comment:
    def __init__(self, comment_id, user_id, text, creation_date):
        self.comment_id = comment_id
        self.user_id = user_id
        self.text = text
        self.creation_date = creation_date

    def to_dict(self):
        return {
            "_id": self.comment_id,
            "userId": self.user_id,
            "text": self.text,
            "creationDate": self.creation_date.isoformat()
        }

class Like:
    def __init__(self, like_id, post_id, user_id, creation_date):
        self.like_id = like_id
        self.post_id = post_id
        self.user_id = user_id
        self.creation_date = creation_date

    def to_dict(self):
        return {
            "_id": self.like_id,
            "post_id": self.post_id,
            "user_id": self.user_id,
            "creationDate": self.creation_date.isoformat()
        }