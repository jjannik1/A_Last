import dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Form, Request, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import pbkdf2_sha256
from datetime import datetime
from bson.objectid import ObjectId
from random import sample
from starlette.middleware.base import BaseHTTPMiddleware
import shutil
import os
from uuid import uuid4
import random
import httpx
import pytz
from dotenv import load_dotenv

load_dotenv()

MAX_IMAGE_SIZE = 10 * 1024 * 1024      # 10MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024      # 50MB

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm"]

UPLOAD_DIR_IMAGES = "static/uploads/post_images"
UPLOAD_DIR_VIDEOS = "static/uploads/post_videos"
FEED_PAGE_LIMIT = 10

os.makedirs(UPLOAD_DIR_IMAGES, exist_ok=True)
os.makedirs(UPLOAD_DIR_VIDEOS, exist_ok=True)

# =====================================================
# APP CONFIG
# =====================================================

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="supersecreto")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================
# DATABASE
# =====================================================

import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://social-mongodb:27017")
client = AsyncIOMotorClient(MONGO_URL)

db = client["social"]
users_collection = db["usuarios"]
posts_collection = db["post"]
comments_collection = db["comentarios"]

# =====================================================
# MIDDLEWARE USER
# =====================================================
# Primero SessionMiddleware



# =====================================================
# AUTH
# =====================================================

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request})


@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    surname1: str = Form(...),
    surname2: str = Form(None),
    profile_image: UploadFile = File(...),
    location: str = Form(...)  # <--- nuevo campo

):
    if await users_collection.find_one({"email": email}):
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": "Email ya registrado"})

    if await users_collection.find_one({"username": username}):
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": "Usuario ya en uso"})

    filename = f"{username}_{profile_image.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(profile_image.file, buffer)

    hashed_password = pbkdf2_sha256.hash(password)

    await users_collection.insert_one({
    "username": username,
    "email": email,
    "password": hashed_password,
    "name": name,
    "surname1": surname1,
    "surname2": surname2,
    "profile_image": f"/static/uploads/{filename}",
    "followers": [],
    "following": [],
    "register_date": datetime.utcnow(),
    "rol": "user",
    "state": "active",
    "theme": "light",
    "location": location  # <--- guardar localidad
})


    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await users_collection.find_one({"username": username})

    if not user:
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Usuario no encontrado"})

    if user.get("state") == "blocked":
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Cuenta bloqueada"})

    if not pbkdf2_sha256.verify(password, user["password"]):
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Contraseña incorrecta"})

    request.session["user"] = {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "rol": user.get("rol", "user"),
        "location": user.get("location", "No especificada")
    }

    return RedirectResponse("/", status_code=303)



@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# =====================================================
# HOME
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    posts = []

    if user:
        user_obj_id = ObjectId(user["id"])
        user_data = await users_collection.find_one({"_id": user_obj_id})

        following_ids = user_data.get("following", [])
        following_obj_ids = []

        for uid in following_ids:
            try:
                following_obj_ids.append(ObjectId(uid))
            except Exception:
                pass  # ignorar si no es ObjectId válido

        # Buscamos posts:
        # 1. Públicos
        # 2. Privados de los que sigo
        # 3. Mis propios privados
        cursor = posts_collection.find({
            "$or": [
                {"visibility": "public"},
                {"visibility": "private", "userId": {"$in": following_obj_ids}},
                {"userId": user_obj_id}  # siempre ver mis posts privados
            ]
        }).sort("creacionDate", -1)

        posts = await cursor.to_list(length=20)

    else:
        # Usuario no logueado: solo posts públicos
        cursor = posts_collection.find({"visibility": "public"}).sort("creacionDate", -1)
        posts = await cursor.to_list(length=20)

    # Enriquecemos los posts con usuario, comentarios y likes
    enriched_posts = []
    for post in posts:
        post_user = await users_collection.find_one({"_id": post["userId"]})
        if not post_user:
            continue

        post["username"] = post_user["username"]
        post["profile_image"] = post_user.get("profile_image")

        # Comentarios completos
        comment_objects = []
        for comment_id in post.get("comments", []):
            comment = await comments_collection.find_one({"_id": comment_id})
            if comment:
                comment_user = await users_collection.find_one({"_id": comment["userId"]})
                comment["username"] = comment_user["username"] if comment_user else "Usuario"
                comment["userId"] = str(comment["userId"])
                from datetime import timezone

# dentro del for comment
                if "creationDate" in comment:
                    dt = comment["creationDate"]

    # Aseguramos que es UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)

                    comment["creationDateFormatted"] = dt.strftime("%H:%M %d/%m/%y")
                comment_objects.append(comment)

        post["comment_objects"] = comment_objects
        post["likes_count"] = len(post.get("likes", []))

        enriched_posts.append(post)

    return templates.TemplateResponse(request, "home.html", {
        "request": request,
        "user": user,
        "posts": enriched_posts
    })




# =====================================================
# PROFILE
# =====================================================

@app.get("/profile/{userid}", response_class=HTMLResponse)
async def profile(request: Request, userid: str):
    user_data = await users_collection.find_one({"_id": ObjectId(userid)})
    if not user_data:
        raise HTTPException(status_code=404)

    session_user = request.session.get("user")

    # 👇 Si es dueño del perfil o admin → ver todo
    if session_user and (
        session_user["id"] == userid or
        session_user.get("rol") == "admin"
    ):
        query = {"userId": ObjectId(userid)}

    # 👇 Si es otro usuario o no está logueado → solo públicos
    else:
        query = {
            "userId": ObjectId(userid),
            "visibility": "public"
        }

    posts_cursor = posts_collection.find(query).sort("creacionDate", -1)
    posts = await posts_cursor.to_list(length=50)

    return templates.TemplateResponse(request, "profile.html", {
        "request": request,
        "user": user_data,
        "posts": posts
    })

# =====================================================
# CONFIG
# =====================================================

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    user_data = await users_collection.find_one({"_id": ObjectId(user["id"])})

    return templates.TemplateResponse(request, "config.html", {
        "request": request,
        "user": user_data
    })


@app.post("/config")
async def update_config(
    request: Request,
    username: str = Form(None),
    name: str = Form(None),
    surname1: str = Form(None),
    surname2: str = Form(None),
    email: str = Form(None),
    theme: str = Form(None),
    location: str = Form(None),
    current_password: str = Form(None),
    new_password: str = Form(None),
    profile_image: UploadFile = File(None)  # 👈 NUEVO
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    user_id = ObjectId(user["id"])
    user_data = await users_collection.find_one({"_id": user_id})

    update_data = {}

    # =========================
    # CAMBIO FOTO PERFIL
    # =========================
    if profile_image and profile_image.filename:

        # borrar foto anterior si no es default
        old_image = user_data.get("profile_image")
        if old_image and "default.png" not in old_image:
            old_path = old_image.replace("/static/", "static/")
            if os.path.exists(old_path):
                os.remove(old_path)

        filename = f"{user_data['username']}_{profile_image.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_image.file, buffer)

        update_data["profile_image"] = f"/static/uploads/{filename}"

    # =========================
    # CAMBIO CONTRASEÑA
    # =========================
    if current_password and new_password:
        if not pbkdf2_sha256.verify(current_password, user_data["password"]):
            return templates.TemplateResponse(request, "config.html", {
                "request": request,
                "user": user_data,
                "error": "Contraseña actual incorrecta"
            })

        update_data["password"] = pbkdf2_sha256.hash(new_password)

    # =========================
    # OTROS CAMPOS (resumido)
    # =========================
    if username and username != user_data["username"]:
        existing_user = await users_collection.find_one({"username": username})
        if existing_user:
            return templates.TemplateResponse(request, "config.html", {
                "request": request,
                "user": user_data,
                "error": "Ese username ya está en uso"
            })
        update_data["username"] = username
        request.session["user"]["username"] = username

    if email and email != user_data["email"]:
        existing_email = await users_collection.find_one({"email": email})
        if existing_email:
            return templates.TemplateResponse(request, "config.html", {
                "request": request,
                "user": user_data,
                "error": "Ese email ya registrado"
            })
        update_data["email"] = email
        request.session["user"]["email"] = email

    if name:
        update_data["name"] = name
    if surname1:
        update_data["surname1"] = surname1
    if surname2:
        update_data["surname2"] = surname2
    if theme:
        update_data["theme"] = theme
    if location:
        update_data["location"] = location

    if update_data:
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )

    return RedirectResponse("/config", status_code=303)

# =====================================================
# DELETE OWN ACCOUNT
# =====================================================

@app.post("/delete-my-account")
async def delete_my_account(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    obj_id = ObjectId(user["id"])

    # 1️⃣ Quitarme de followers/following de otros
    await users_collection.update_many(
        {"followers": user["id"]},
        {"$pull": {"followers": user["id"]}}
    )
    await users_collection.update_many(
        {"following": user["id"]},
        {"$pull": {"following": user["id"]}}
    )

    # 2️⃣ Eliminar comentarios del usuario y guardar IDs
    deleted_comments_cursor = comments_collection.find({"userId": obj_id}, {"_id": 1})
    deleted_comment_ids = [c["_id"] async for c in deleted_comments_cursor]
    await comments_collection.delete_many({"userId": obj_id})

    # 3️⃣ Limpiar comentarios del usuario en posts existentes
    if deleted_comment_ids:
        await posts_collection.update_many(
            {"comments": {"$in": deleted_comment_ids}},
            {"$pull": {"comments": {"$in": deleted_comment_ids}}}
        )

    # 4️⃣ Quitar likes del usuario en posts existentes
    await posts_collection.update_many(
        {"likes": user["id"]},
        {"$pull": {"likes": user["id"]}}
    )

    # 5️⃣ Eliminar posts del usuario
    await posts_collection.delete_many({"userId": obj_id})

    # 6️⃣ Limpiar posts de otros usuarios que quedaron vacíos de interacción
    await posts_collection.delete_many({
        "$and": [
            {"comments": {"$size": 0}},
            {"likes": {"$size": 0}}
        ]
    })

    # 7️⃣ Eliminar al usuario
    await users_collection.delete_one({"_id": obj_id})

    request.session.clear()

    return RedirectResponse("/", status_code=303)


@app.post("/delete-my-post/{postid}")
async def delpost(request: Request, postid: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    objpost = ObjectId(postid)
    objuser = ObjectId(user["id"])

    # 1️⃣ Buscar el post y verificar que es del usuario
    post = await posts_collection.find_one({"_id": objpost})

    if not post or post["userId"] != objuser:
        raise HTTPException(status_code=403, detail="No autorizado")

    # 2️⃣ Borrar todos los comentarios del post
    comment_ids = post.get("comments", [])
    if comment_ids:
        await comments_collection.delete_many({"_id": {"$in": comment_ids}})

    # 3️⃣ Borrar el post
    await posts_collection.delete_one({"_id": objpost})

    return RedirectResponse("/", status_code=303)

@app.post("/delete-my-comment/{commentid}")
async def delcom(request: Request, commentid: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    objcomm = ObjectId(commentid)
    objuser = ObjectId(user["id"])

    comment = await comments_collection.find_one({"_id": objcomm})

    if not comment or comment["userId"] != objuser:
        return JSONResponse({"error": "No autorizado"}, status_code=403)

    # Borrar comentario
    await comments_collection.delete_one({"_id": objcomm})

    # Quitar referencia del post
    await posts_collection.update_many(
        {"comments": objcomm},
        {"$pull": {"comments": objcomm}}
    )

    # Devolver info para que el frontend actualice la UI
    return JSONResponse({
        "success": True,
        "comment_id": commentid,
        "userId": user["id"]
    })

@app.get("/comments/{post_id}")
async def get_comments(post_id: str):
    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return JSONResponse([], status_code=404)

    comments = []
    for cid in post.get("comments", []):
        comment = await comments_collection.find_one({"_id": cid})
        if comment:
            user = await users_collection.find_one({"_id": comment["userId"]})
            comments.append({
                "id": str(comment["_id"]),
                "text": comment["text"],
                "username": user["username"] if user else "Usuario",
                "userId": str(comment["userId"]),
                "creationDate": str(comment["creationDate"])
            })

    return JSONResponse(comments)

"""
@app.post("/delete-my-comment/{commentid}")
async def delcom(request: Request, commentid: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    objcomm = ObjectId(commentid)
    objuser = ObjectId(user["id"])

    # 1️⃣ Buscar comentario
    comment = await comments_collection.find_one({"_id": objcomm})

    if not comment or comment["userId"] != objuser:
        raise HTTPException(status_code=403, detail="No autorizado")

    # 2️⃣ Eliminar comentario
    await comments_collection.delete_one({"_id": objcomm})

    # 3️⃣ Quitar referencia del post
    await posts_collection.update_many(
        {"comments": objcomm},
        {"$pull": {"comments": objcomm}}
    )

    return RedirectResponse("/", status_code=303)
"""
# =====================================================
# ADMIN
# =====================================================

def admin_required(user):
    return user and user.get("rol") == "admin"


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = request.session.get("user")
    if not admin_required(user):
        return RedirectResponse("/logout", status_code=303)

    total_users = await users_collection.count_documents({})
    total_posts = await posts_collection.count_documents({})
    total_comments = await comments_collection.count_documents({})
    blocked_users = await users_collection.count_documents({"state": "blocked"})

    all_users_cursor = users_collection.find({})
    all_users = await all_users_cursor.to_list(length=100)

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "stats": {
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "blocked": blocked_users
        },
        "all_users": all_users
    })


@app.post("/admin/toggle-block/{userid}")
async def toggle_block_user(request: Request, userid: str):
    user = request.session.get("user")
    if not admin_required(user):
        return RedirectResponse("/logout", status_code=303)

    target = await users_collection.find_one({"_id": ObjectId(userid)})
    if not target:
        raise HTTPException(status_code=404)

    new_state = "blocked" if target.get("state") == "active" else "active"

    await users_collection.update_one(
        {"_id": ObjectId(userid)},
        {"$set": {"state": new_state}}
    )

    return RedirectResponse(f"/profile/{userid}", status_code=303)


@app.post("/admin/delete/{userid}")
async def admin_delete_user(request: Request, userid: str):
    user = request.session.get("user")
    if not admin_required(user):
        return RedirectResponse("/logout", status_code=303)

    obj_id = ObjectId(userid)

    # Quitar el usuario de followers/following
    await users_collection.update_many(
        {"followers": userid},
        {"$pull": {"followers": userid}}
    )
    await users_collection.update_many(
        {"following": userid},
        {"$pull": {"following": userid}}
    )

    # Eliminar comentarios y posts
    deleted_comments = await comments_collection.delete_many({"userId": obj_id})
    deleted_posts = await posts_collection.delete_many({"userId": obj_id})

    # Eliminar el usuario
    await users_collection.delete_one({"_id": obj_id})

    print(f"Admin eliminó usuario {userid}, posts borrados: {deleted_posts.deleted_count}, comentarios borrados: {deleted_comments.deleted_count}")

    return RedirectResponse("/admin/dashboard", status_code=303)


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = Query(None)):
    users = []

    if q:
        cursor = users_collection.find({
            "username": {"$regex": q, "$options": "i"}
        })
        users = await cursor.to_list(length=20)

    return templates.TemplateResponse(request, "search.html", {
        "request": request,
        "users": users,
        "query": q
    })
@app.post("/create-post")
async def create_post(
    request: Request,
    text: str = Form(...),
    visibility: str = Form("public"),
    media: list[UploadFile] = File(None)  # ✅ puede ser None
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    images_urls = []
    videos_urls = []

    if media:  # solo procesamos si hay archivos
        for f in media:
            if not f.filename:  # ❌ ignorar archivos sin nombre
                continue

            content = await f.read()
            size = len(content)
            extension = f.filename.split(".")[-1]
            filename = f"{uuid4().hex}.{extension}"

            if f.content_type in ALLOWED_IMAGE_TYPES:
                if size > MAX_IMAGE_SIZE:
                    raise HTTPException(status_code=400, detail=f"Imagen demasiado grande: {f.filename}")
                file_path = os.path.join(UPLOAD_DIR_IMAGES, filename)
                with open(file_path, "wb") as buf:
                    buf.write(content)
                images_urls.append("/" + file_path.replace("\\", "/"))

            elif f.content_type in ALLOWED_VIDEO_TYPES:
                if size > MAX_VIDEO_SIZE:
                    raise HTTPException(status_code=400, detail=f"Video demasiado grande: {f.filename}")
                file_path = os.path.join(UPLOAD_DIR_VIDEOS, filename)
                with open(file_path, "wb") as buf:
                    buf.write(content)
                videos_urls.append("/" + file_path.replace("\\", "/"))

            else:
                raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {f.filename}")

    await posts_collection.insert_one({
        "userId": ObjectId(user["id"]),
        "text": text,
        "images": images_urls,  # puede estar vacío
        "videos": videos_urls,  # puede estar vacío
        "visibility": visibility,
        "likes": [],
        "comments": [],
        "creacionDate": datetime.utcnow()
    })

    return RedirectResponse("/", status_code=303)

@app.post("/follow/{userid}")
async def follow_user(request: Request, userid: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    if user["id"] == userid:
        return RedirectResponse("/", status_code=303)

    await users_collection.update_one(
        {"_id": ObjectId(user["id"])},
        {"$addToSet": {"following": userid}}
    )

    await users_collection.update_one(
        {"_id": ObjectId(userid)},
        {"$addToSet": {"followers": user["id"]}}
    )

    return RedirectResponse(f"/profile/{userid}", status_code=303)

@app.post("/comment")
async def create_comment(request: Request, post_id: str = Form(...), text: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No logueado"}, status_code=401)

    creation_date = datetime.utcnow()

    comment_doc = {
        "userId": ObjectId(user["id"]),
        "text": text,
        "creationDate": creation_date
    }

    result = await comments_collection.insert_one(comment_doc)

    # Añadir a post
    await posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"comments": result.inserted_id}}
    )

    # Devuelve info necesaria para actualizar UI
    return JSONResponse({
        "comment_id": str(result.inserted_id),
        "username": user["username"],
        "text": text,
        "creationDate": creation_date.isoformat()
    })
@app.get("/create-post", response_class=HTMLResponse)
async def create_post_page(request: Request):
    # Revisamos si el usuario está logueado
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(request, "create_post.html", {
        "request": request,
        "user": user
    })

@app.post("/like/{post_id}")
async def like_post(request: Request, post_id: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No logueado"}, status_code=401)

    await posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$addToSet": {"likes": user["id"]}}
    )

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    likes_count = len(post.get("likes", []))
    liked = user["id"] in post.get("likes", [])

    return JSONResponse({"liked": liked, "likes_count": likes_count})


@app.post("/dislike/{post_id}")
async def dislike_post(request: Request, post_id: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No logueado"}, status_code=401)

    await posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$pull": {"likes": user["id"]}}
    )

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    likes_count = len(post.get("likes", []))
    liked = user["id"] in post.get("likes", [])

    return JSONResponse({"liked": liked, "likes_count": likes_count})

@app.get("/navbar-info")
async def navbar_info(request: Request):
    user = request.session.get("user")
    if not user:
        return {"time": None, "weather": None}

    user_data = await users_collection.find_one({"_id": ObjectId(user["id"])})
    if not user_data:
        return {"time": None, "weather": None}

    location = user_data.get("location")
    if not location:
        return {"time": None, "weather": None}

    # 1️⃣ Geocodificar ciudad (OpenStreetMap Nominatim)
    lat, lon = None, None
    try:
        async with httpx.AsyncClient() as client:
            nom_url = f"https://nominatim.openstreetmap.org/search?city={location}&format=json"
            res = await client.get(nom_url, headers={"User-Agent": "SocialApp"})
            geo = res.json()
            if len(geo) > 0:
                lat = float(geo[0]["lat"])
                lon = float(geo[0]["lon"])
    except:
        pass

    # Si no hay coordenadas, enviar vacío
    if not lat or not lon:
        return {"time": None, "weather": None}

    # 2️⃣ Clima con Open‑Meteo (sin API key ⚡)
    weather = None
    try:
        async with httpx.AsyncClient() as client:
            wm_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            resw = await client.get(wm_url)
            if resw.status_code == 200:
                weather = resw.json().get("current_weather")
    except:
        weather = None

    # 3️⃣ Hora con WorldTimeAPI
    time = None
    try:
        async with httpx.AsyncClient() as client:
            wm_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            resw = await client.get(wm_url)
            if resw.status_code == 200:
                weather_data = resw.json().get("current_weather")
                weather = weather_data

                # Obtenemos hora actual según timezone
                timezone = resw.json().get("timezone")
                if timezone:
                    # Solo hora en formato HH:MM
                    now = datetime.now(pytz.timezone(timezone))
                    time = now.strftime("%H:%M")
    except:
        weather = None
        time = None

    return {"time": time, "weather": weather, "location": location}

@app.get("/feed", response_class=HTMLResponse)
async def feed_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    user_obj_id = ObjectId(user["id"])
    
    # Guardamos IDs de posts ya vistos en la sesión
    seen_posts = request.session.get("seen_posts", [])

    # Obtenemos todos los posts públicos o privados de usuarios que sigo
    user_data = await users_collection.find_one({"_id": user_obj_id})
    following_ids = [ObjectId(uid) for uid in user_data.get("following", []) if ObjectId.is_valid(uid)]

    cursor = posts_collection.find({
        "$or": [
            {"visibility": "public"},
            {"visibility": "private", "userId": {"$in": following_ids}}
        ],
        "_id": {"$nin": [ObjectId(pid) for pid in seen_posts]}  # evitamos repetir
    })

    all_posts = await cursor.to_list(length=None)

    # Seleccionamos aleatoriamente FEED_PAGE_LIMIT posts
    if len(all_posts) > FEED_PAGE_LIMIT:
        random_posts = random.sample(all_posts, FEED_PAGE_LIMIT)
    else:
        random_posts = all_posts

    # Añadimos IDs a sesión para no repetirlos
    new_seen_posts = seen_posts + [str(p["_id"]) for p in random_posts]
    request.session["seen_posts"] = new_seen_posts

    # Enriquecemos posts con username y profile_image
    enriched_posts = []
    for post in random_posts:
        post_user = await users_collection.find_one({"_id": post["userId"]})
        if not post_user:
            continue
        post["username"] = post_user["username"]
        post["profile_image"] = post_user.get("profile_image")
        enriched_posts.append(post)

    return templates.TemplateResponse(request, "feed.html", {
        "request": request,
        "user": user,
        "posts": enriched_posts
    })

@app.get("/feed/load-more", response_class=HTMLResponse)
async def feed_load_more(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="No autorizado")

    user_obj_id = ObjectId(user["id"])
    seen_posts = request.session.get("seen_posts", [])

    user_data = await users_collection.find_one({"_id": user_obj_id})
    following_ids = [ObjectId(uid) for uid in user_data.get("following", []) if ObjectId.is_valid(uid)]

    cursor = posts_collection.find({
        "$or": [
            {"visibility": "public"},
            {"visibility": "private", "userId": {"$in": following_ids}}
        ],
        "_id": {"$nin": [ObjectId(pid) for pid in seen_posts]}
    })

    all_posts = await cursor.to_list(length=None)
    if not all_posts:
        return HTMLResponse("")  # No hay más posts

    FEED_PAGE_LIMIT = 10
    if len(all_posts) > FEED_PAGE_LIMIT:
        random_posts = random.sample(all_posts, FEED_PAGE_LIMIT)
    else:
        random_posts = all_posts

    # Añadimos IDs a sesión
    request.session["seen_posts"] = seen_posts + [str(p["_id"]) for p in random_posts]

    # Enriquecemos posts con username y profile_image
    enriched_posts = []
    for post in random_posts:
        post_user = await users_collection.find_one({"_id": post["userId"]})
        if not post_user:
            continue
        post["username"] = post_user["username"]
        post["profile_image"] = post_user.get("profile_image")
        enriched_posts.append(post)

    # Renderizamos solo los posts como HTML parcial
    return templates.TemplateResponse(request, "feed_posts_partial.html", {
        "request": request,
        "posts": enriched_posts
    })

# =====================================================
# CHAT SYSTEM
# =====================================================
from typing import Dict, List
import json

messages_collection = db["mensajes"]

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    current_uid = user["id"]
    
    # Obtener usuarios con los que interactuar (recientes)
    sent_msgs = await messages_collection.distinct("receiver_id", {"sender_id": current_uid})
    rcvd_msgs = await messages_collection.distinct("sender_id", {"receiver_id": current_uid})
    
    contacted_ids = list(set(sent_msgs + rcvd_msgs))
    
    obj_ids = []
    for cid in contacted_ids:
        try:
            obj_ids.append(ObjectId(cid))
        except:
            pass
            
    recent_users_cursor = users_collection.find({"_id": {"$in": obj_ids}})
    other_users = await recent_users_cursor.to_list(length=100)
    
    # Serializar ObjectId to string para uso fácil en el template
    for u in other_users:
        u["_id"] = str(u["_id"])
    
    return templates.TemplateResponse(request, "chat.html", {
        "request": request,
        "user": user,
        "other_users": other_users
    })

@app.get("/api/chat/search")
async def search_chat_users(request: Request, q: str = Query("")):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No autorizado"}, status_code=401)
        
    if not q:
        return JSONResponse([])
        
    cursor = users_collection.find({
        "username": {"$regex": q, "$options": "i"},
        "_id": {"$ne": ObjectId(user["id"])}
    }).limit(10)
    
    results = await cursor.to_list(length=10)
    users = [{"_id": str(u["_id"]), "username": u["username"], "profile_image": u.get("profile_image", "/static/uploads/default.png")} for u in results]
    
    return JSONResponse(users)

@app.get("/api/chat/history/{other_user_id}")
async def get_chat_history(
    request: Request,
    other_user_id: str,
    after: str = None
):
    user = request.session.get("user")

    if not user:
        return JSONResponse(
            {"error": "No autorizado"},
            status_code=401
        )

    current_user = user["id"]

    query = {
        "$or": [
            {
                "sender_id": current_user,
                "receiver_id": other_user_id
            },
            {
                "sender_id": other_user_id,
                "receiver_id": current_user
            }
        ]
    }

    # SOLO mensajes nuevos
    if after:
        query["timestamp"] = {
            "$gt": datetime.fromisoformat(after)
        }

    cursor = messages_collection.find(query).sort(
        "timestamp",
        1
    )

    messages = await cursor.to_list(length=100)

    # Marcar mensajes recibidos como leídos
    await messages_collection.update_many(
        {
            "sender_id": other_user_id,
            "receiver_id": current_user,
            "read": False
        },
        {
            "$set": {
                "read": True
            }
        }
    )

    for msg in messages:
        msg["_id"] = str(msg["_id"])
        msg["timestamp"] = msg["timestamp"].isoformat()

    return JSONResponse(messages)

@app.post("/api/chat/send")
async def send_message(request: Request):

    user = request.session.get("user")

    if not user:
        return JSONResponse(
            {"error": "No autorizado"},
            status_code=401
        )

    data = await request.json()

    receiver_id = data.get("receiver_id")
    content = data.get("content")

    if not receiver_id or not content:
        return JSONResponse(
            {"error": "Datos inválidos"},
            status_code=400
        )

    new_msg = {
        "sender_id": user["id"],
        "receiver_id": receiver_id,
        "content": content,
        "timestamp": datetime.utcnow(),
        "read": False
    }

    result = await messages_collection.insert_one(new_msg)

    new_msg["_id"] = str(result.inserted_id)
    new_msg["timestamp"] = new_msg["timestamp"].isoformat()

    return JSONResponse(new_msg)

@app.get("/api/chat/unread")
async def unread_messages(request: Request):

    user = request.session.get("user")

    if not user:
        return JSONResponse(
            {"error": "No autorizado"},
            status_code=401
        )

    unread = await messages_collection.aggregate([
        {
            "$match": {
                "receiver_id": user["id"],
                "read": False
            }
        },
        {
            "$group": {
                "_id": "$sender_id",
                "count": {
                    "$sum": 1
                }
            }
        }
    ]).to_list(length=100)

    return JSONResponse(unread)