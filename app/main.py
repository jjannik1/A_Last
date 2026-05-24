from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, Form, Request, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import pbkdf2_sha256
from datetime import datetime
from datetime import timezone
from bson.objectid import ObjectId
from random import sample
import shutil
import os
from uuid import uuid4
import random
from random import shuffle
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
UPLOAD_DIR_PROFILE = "static/uploads/profile_pictures"
FEED_PAGE_LIMIT = 10

# Si tiene existe no dara problemas el parametro exist_ok=True

os.makedirs(UPLOAD_DIR_IMAGES, exist_ok=True)
os.makedirs(UPLOAD_DIR_VIDEOS, exist_ok=True)
os.makedirs(UPLOAD_DIR_PROFILE, exist_ok=True)

# =====================================================
# APP CONFIG
# =====================================================

app = FastAPI()
#Usamos jinja2 para renderizar html, esta en la carpeta templates
templates = Jinja2Templates(directory="templates")

#Montamos staticfiles para poder acceder a los archivos estaticos si no lo tenemos, no podramos acceder a esos archivos estaticos
app.mount("/static", StaticFiles(directory="static"), name="static")

#Usamos session middleware para gestionar sesiones
#Un middleware es la conexion entre el frontend y el backend, antes de que la peticion llegue al backend se ejecuta el middleware
#Se usa para guardar datos del usuario entre peticiones
app.add_middleware(SessionMiddleware, secret_key="supersecreto")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================
# DATABASE
# =====================================================


MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)

db = client["social"]
users_collection = db["usuarios"]
posts_collection = db["post"]
comments_collection = db["comentarios"]


# =====================================================
# REGISTER
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
    profile_image: UploadFile = File(None),
    location: str = Form(...)  # Campo necesario para poder poner el tiempo y el clima de esa localidad
):
# Si existe uno de esos dara fallo con un mensaje de error
    if await users_collection.find_one({"email": email}):
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": "Email ya registrado"})

    if await users_collection.find_one({"username": username}):
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": "Usuario ya en uso"})

    ruta_imagen = None
    if profile_image and profile_image.filename:

        filename = profile_image.filename
        file_path = os.path.join(UPLOAD_DIR_PROFILE, filename)

        #Metemox el archivo binario (b en wb) y lo leemos y lo guardamos

        with open(file_path, "wb") as f:
            f.write(await profile_image.read())  # <-- leer y guardar foto de perfil

        ruta_imagen = f"/{UPLOAD_DIR_PROFILE}/{filename}".replace("\\", "/")

    hashed_password = pbkdf2_sha256.hash(password)

    await users_collection.insert_one({
    "username": username,
    "email": email,
    "password": hashed_password,
    "name": name,
    "surname1": surname1,
    "surname2": surname2,
    "profile_image": ruta_imagen,
    "followers": [],
    "following": [],
    "register_date": datetime.utcnow(),
    "rol": "user",
    "state": "active",
    "location": location
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
        "role": user.get("role", "user"),
        "location": user.get("location", "No especificada")
    }

    #  SI ES ADMIN, REDIRIGIR AL DASHBOARD DIRECTAMENTE
    if user.get("role") == "admin":
        return RedirectResponse("/admin/dashboard", status_code=303)

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

    # 1. COMPROBACIÓN Y CREACIÓN DEL ADMIN AUTOMÁTICO
    admin_user = await users_collection.find_one({"username": "admin"})
    if not admin_user:
        # Hasheamos la contraseña de forma segura con pbkdf2_sha256
        hashed_password = pbkdf2_sha256.hash("Admin1234")
        
        await users_collection.insert_one({
            "username": "admin",
            "password": hashed_password,
            "role": "admin",
            "email": "admin@socialapp.com",
            "profile_image": None,
            "following": [],
            "followers": []
        })

    user = request.session.get("user")
    posts = []
    seen_posts = []

    if user:
        user_obj_id = ObjectId(user["id"])
        user_data = await users_collection.find_one({"_id": user_obj_id})

        following_ids = user_data.get("following", [])
        following_obj_ids = []
        for uid in following_ids:
            try:
                following_obj_ids.append(ObjectId(uid))
            except Exception:
                pass

        # 1. Posts de los que sigo y mis propios posts
        cursor_following = posts_collection.find({
            "$or": [
                {"visibility": "public", "userId": {"$in": following_obj_ids}},
                {"visibility": "private", "userId": {"$in": following_obj_ids}},
                {"userId": user_obj_id}
            ]
        }).sort("creacionDate", -1)

        posts = await cursor_following.to_list(length=20)
        for post in posts:

            post_id = post["_id"]

            post_id_str = str(post_id)

            seen_posts.append(post_id_str)


        # 2. Si faltan para llegar a 20, rellenar con posts públicos aleatorios (que no sean de los seguidos ni mios)
        if len(posts) < 20:
            exclude_ids = following_obj_ids + [user_obj_id]
            cursor_others = posts_collection.find({
                "visibility": "public",
                "userId": {"$nin": exclude_ids}
                #nin = Not in, busqueda de mongodb exclusivo
            })
            other_posts = await cursor_others.to_list(length=None)
            random.shuffle(other_posts)
            needed = 20 - len(posts)
            for post in other_posts[:needed]:

                # Añadir post a la lista principal
                posts.append(post)

                # Obtener id del post
                post_id = post["_id"]

                # Convertir ObjectId a string
                post_id_str = str(post_id)

                seen_posts.append(post_id_str)
        request.session["seen_posts"] = seen_posts

    else:
        # Usuario no logueado: solo posts públicos aleatorios
        cursor = posts_collection.find({"visibility": "public"})
        #Daba fallo porque el motor de mongo necesita el parametro lenght si no, no funciona
        all_public = await cursor.to_list(length=None)
        random.shuffle(all_public)
        posts = all_public[:20]
        for post in posts:

            post_id = post["_id"]
            post_id_str = str(post_id)
            seen_posts.append(post_id_str)

        request.session["seen_posts"] = seen_posts

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

                if "creationDate" in comment:
                    dt = comment["creationDate"]
                    comment["creationDateFormatted"] = dt.strftime("%H:%M %d/%m/%y")
                else:
                    comment["creationDateFormatted"] = ""
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
    try:
        obj_user_id = ObjectId(userid)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")

    user_data = await users_collection.find_one({"_id": obj_user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    session_user = request.session.get("user")

    # Comprobamos si el usuario actual es el dueño del perfil o un administrador del sistema.
    if session_user and (
        session_user["id"] == userid or
        session_user.get("role") == "admin"
    ):
        # Si tiene permisos, puede ver TODAS las publicaciones (tanto las públicas como las privadas).
        # (Se busca tanto por ObjectId como por string para asegurar retrocompatibilidad en la BBDD).
        query = {"userId": {"$in": [obj_user_id, userid]}}

    # Si es un visitante externo u otro usuario, solo ve los públicos
    else:
        query = {
            "userId": {"$in": [obj_user_id, userid]},
            "visibility": "public"
        }

#Mostrar todos los posts, los recientes primeros
    posts_cursor = posts_collection.find(query).sort("creacionDate", -1)
    posts = await posts_cursor.to_list(length=None)

    # Convertimos los _id a string para que Jinja2 no tenga problemas al renderizarlos
    user_data["_id"] = str(user_data["_id"])
    for post in posts:
        post["_id"] = str(post["_id"])

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
    location: str = Form(None),
    current_password: str = Form(None),
    new_password: str = Form(None),
    profile_image: UploadFile = File(None)  # Campo opcional para subir nueva foto de perfil
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

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}-{profile_image.filename}"
        file_path = os.path.join(UPLOAD_DIR_PROFILE, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await profile_image.read())

        update_data["profile_image"] = f"/{UPLOAD_DIR_PROFILE}/{filename}".replace("\\", "/")

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

    #  Quitarme de followers/following de otros
    await users_collection.update_many(
        {"followers": {"$in": [obj_id, user["id"]]}},
        {"$pull": {"followers": {"$in": [obj_id, user["id"]]}}}
    )
    await users_collection.update_many(
        {"following": {"$in": [obj_id, user["id"]]}},
        {"$pull": {"following": {"$in": [obj_id, user["id"]]}}}
    )

    # Eliminar comentarios del usuario y guardar IDs
    deleted_comments_cursor = comments_collection.find({"userId": obj_id}, {"_id": 1})
    deleted_comment_ids = []

    async for comment in deleted_comments_cursor:
        deleted_comment_ids.append(comment["_id"])

    #  Limpiar comentarios del usuario en posts existentes
    if deleted_comment_ids:
        await posts_collection.update_many(
            {"comments": {"$in": deleted_comment_ids}},
            {"$pull": {"comments": {"$in": deleted_comment_ids}}}
        )
        # Delete the actual comments from the collection
        await comments_collection.delete_many({"userId": obj_id})

    #  Quitar likes del usuario en posts existentes
    await posts_collection.update_many(
        {"likes": {"$in": [obj_id, user["id"]]}},
        {"$pull": {"likes": {"$in": [obj_id, user["id"]]}}}
    )

    #  Eliminar posts del usuario
    await posts_collection.delete_many({"userId": obj_id})

    #  Eliminar al usuario
    await users_collection.delete_one({"_id": obj_id})

    request.session.clear()

    return RedirectResponse("/", status_code=303)


@app.post("/delete-my-post/{postid}")
async def delpost(request: Request, postid: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login", status_code=303)

    try:
        objpost = ObjectId(postid)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de post inválido")

    # 1️⃣ Buscar el post
    post = await posts_collection.find_one({"_id": objpost})
    if not post:
        raise HTTPException(status_code=404, detail="El post no existe")

    # Convertimos los IDs a string para comparar texto con texto de forma segura
    post_owner_id = str(post.get("userId"))
    current_user_id = str(user.get("id"))
    user_role = user.get("role")  # O 'rol' según como lo tengas en tu sesión

    # Permite borrar si el usuario actual es el dueño O si es administrador
    if post_owner_id == current_user_id or user_role == "admin":
        
        # 2️⃣ Borrar todos los comentarios del post
        comment_ids = post.get("comments", [])
        if comment_ids:
            await comments_collection.delete_many({"_id": {"$in": comment_ids}})

        # 3️⃣ Borrar el post
        await posts_collection.delete_one({"_id": objpost})

        # Redireccionar de vuelta al perfil del dueño del post o al inicio
        return RedirectResponse(f"/profile/{post_owner_id}", status_code=303)
    
    # Si no es dueño ni admin, lanzar error 403
    raise HTTPException(status_code=403, detail="No autorizado")

@app.post("/delete-my-comment/{commentid}")
async def delcom(request: Request, commentid: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    objcomm = ObjectId(commentid)
    objuser = ObjectId(user["id"])

    comment = await comments_collection.find_one({"_id": objcomm})

    if not comment:
        return JSONResponse({"error": "No encontrado"}, status_code=404)

    if comment["userId"] != objuser and user.get("role") != "admin":
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

# =====================================================
# ADMIN
# =====================================================

def admin_required(user):
    return user and user.get("role") == "admin"


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


@app.post("/admin/toggle-block/{user_id}")
async def toggle_block(user_id: str, request: Request):
    current_user = request.session.get("user")
    
    # CORREGIDO: Ahora cualquier usuario con rol admin puede usarlo, no solo el user 'admin'
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
        
    user_data = await users_collection.find_one({"_id": obj_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    current_state = user_data.get("state", "active")
    if current_state == "active":
        new_state = "blocked"
    else:
        new_state = "active"
    
    await users_collection.update_one({"_id": obj_id}, {"$set": {"state": new_state}})
    return RedirectResponse(url=f"/profile/{user_id}", status_code=303)

@app.post("/admin/delete/{user_id}")
async def delete_user(user_id: str, request: Request):
    current_user = request.session.get("user")
    
    # CORREGIDO: Validación por rol admin global
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
        
    # Limpiar de followers/following de otros
    await users_collection.update_many(
        {"followers": {"$in": [obj_id, user_id]}},
        {"$pull": {"followers": {"$in": [obj_id, user_id]}}}
    )
    await users_collection.update_many(
        {"following": {"$in": [obj_id, user_id]}},
        {"$pull": {"following": {"$in": [obj_id, user_id]}}}
    )

    # Eliminar comentarios del usuario y guardar IDs
    deleted_comments_cursor = comments_collection.find({"userId": obj_id}, {"_id": 1})
    deleted_comment_ids = []
    async for comment in deleted_comments_cursor:
        deleted_comment_ids.append(comment["_id"])

    # Limpiar comentarios del usuario en posts existentes
    if deleted_comment_ids:
        await posts_collection.update_many(
            {"comments": {"$in": deleted_comment_ids}},
            {"$pull": {"comments": {"$in": deleted_comment_ids}}}
        )
        # Eliminar los comentarios reales de la colección
        await comments_collection.delete_many({"userId": obj_id})

    # Quitar likes del usuario en posts existentes
    await posts_collection.update_many(
        {"likes": {"$in": [obj_id, user_id]}},
        {"$pull": {"likes": {"$in": [obj_id, user_id]}}}
    )

    # Borrar posts y usuario
    await posts_collection.delete_many({"userId": obj_id})
    await users_collection.delete_one({"_id": obj_id})
    
    return RedirectResponse(url="/", status_code=303)

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
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}-{f.filename}"

            if f.content_type in ALLOWED_IMAGE_TYPES:
                if size > MAX_IMAGE_SIZE:
                    return templates.TemplateResponse(request, "create_post.html", {"request": request, "user": user, "error": f"La imagen '{f.filename}' es demasiado grande (máximo 10MB)."})
                file_path = os.path.join(UPLOAD_DIR_IMAGES, filename)
                with open(file_path, "wb") as buf:
                    buf.write(content)
                images_urls.append("/" + file_path.replace("\\", "/"))

            elif f.content_type in ALLOWED_VIDEO_TYPES:
                if size > MAX_VIDEO_SIZE:
                    return templates.TemplateResponse(request, "create_post.html", {"request": request, "user": user, "error": f"El video '{f.filename}' es demasiado grande (máximo 50MB)."})
                file_path = os.path.join(UPLOAD_DIR_VIDEOS, filename)
                with open(file_path, "wb") as buf:
                    buf.write(content)
                videos_urls.append("/" + file_path.replace("\\", "/"))

            else:
                return templates.TemplateResponse(request, "create_post.html", {"request": request, "user": user, "error": f"El archivo '{f.filename}' no es válido. Solo se permiten imágenes y videos."})

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

@app.post("/follow/{user_id}")
async def follow_user(user_id: str, request: Request):
    session_user = request.session.get("user")
    if not session_user:
        return RedirectResponse("/login", status_code=303)

    current_user_id = session_user["id"]
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="No puedes seguirte a ti mismo")

    try:
        target_uid = ObjectId(user_id)
        current_uid = ObjectId(current_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")

    # Guardar en base de datos
    await users_collection.update_one({"_id": current_uid}, {"$addToSet": {"following": target_uid}})
    await users_collection.update_one({"_id": target_uid}, {"$addToSet": {"followers": current_uid}})

    target_user = await users_collection.find_one({"_id": target_uid})
    followers_count = len(target_user.get("followers", []))

    return JSONResponse({"success": True, "following": True, "followers_count": followers_count})

@app.post("/unfollow/{user_id}")
async def unfollow_user(user_id: str, request: Request):
    # 1. Validar sesión del usuario
    session_user = request.session.get("user")
    if not session_user:
        return RedirectResponse("/login", status_code=303)

    current_user_id = session_user["id"]

    # Evitar que un usuario intente dejarse de seguir a sí mismo
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="No puedes dejar de seguirte a ti mismo")

    try:
        target_uid = ObjectId(user_id)
        current_uid = ObjectId(current_user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")

    # Quitar en base de datos usando ObjectIds
    await users_collection.update_one({"_id": current_uid}, {"$pull": {"following": target_uid}})
    await users_collection.update_one({"_id": target_uid}, {"$pull": {"followers": current_uid}})

    target_user = await users_collection.find_one({"_id": target_uid})
    followers_count = len(target_user.get("followers", []))

    return JSONResponse({"success": True, "following": False, "followers_count": followers_count})

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
    lat = None
    lon = None
    try:
        async with httpx.AsyncClient() as client:
            nom_url = "https://nominatim.openstreetmap.org/search?city=" + location + "&format=json"
            res = await client.get(nom_url, headers={"User-Agent": "SocialApp"})
            geo = res.json()
            if len(geo) > 0:
                lat = float(geo[0]["lat"])
                lon = float(geo[0]["lon"])
            else:
                lat = None
                lon = None
    except Exception as e:
        lat = None
        lon = None

    if lat == None:
        return {"time": None, "weather": None, "location": location}
    else:
        if lon == None:
            return {"time": None, "weather": None, "location": location}

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
    
    # IMPORTANTE: Al entrar a la página limpia de cero, vaciamos los vistos
    seen_posts = []
    request.session["seen_posts"] = seen_posts

    # Obtenemos todos los posts públicos o privados de usuarios que sigo
    user_data = await users_collection.find_one({"_id": user_obj_id})
    following_ids = [ObjectId(uid) for uid in user_data.get("following", []) if ObjectId.is_valid(uid)]

    cursor = posts_collection.find({
        "$or": [
            {"visibility": "public"},
            {"visibility": "private", "userId": {"$in": following_ids}}
        ]
    })

    all_posts = await cursor.to_list(length=None)

    # Seleccionamos aleatoriamente un límite de 20 posts
    FEED_PAGE_LIMIT = 20
    if len(all_posts) > FEED_PAGE_LIMIT:
        random_posts = random.sample(all_posts, FEED_PAGE_LIMIT)
    else:
        random_posts = all_posts

    # Añadimos IDs a sesión para no repetirlos en el "Cargar más"
    request.session["seen_posts"] = [str(p["_id"]) for p in random_posts]

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
    seen_posts = request.session.get("seen_posts", [])
    seen_obj_ids = [ObjectId(pid) for pid in seen_posts if ObjectId.is_valid(pid)]

    posts = []

    if user:
        user_obj_id = ObjectId(user["id"])
        user_data = await users_collection.find_one({"_id": user_obj_id})
        following_ids = []
        for uid in user_data.get("following", []):
            try:
                following_ids.append(ObjectId(uid))
            except Exception:
                pass

        # Excluimos los posts guardados en 'seen_posts'
        cursor_following = posts_collection.find({
            "$or": [
                {"visibility": "public", "userId": {"$in": following_ids}},
                {"visibility": "private", "userId": {"$in": following_ids}},
                {"userId": user_obj_id}
            ],
            "_id": {"$nin": seen_obj_ids}
        }).sort("creacionDate", -1)

        followed_posts = await cursor_following.to_list(length=20)
        posts.extend(followed_posts)

        if len(posts) < 20:
            exclude_ids = following_ids + [user_obj_id]
            cursor_others = posts_collection.find({
                "visibility": "public",
                "userId": {"$nin": exclude_ids},
                "_id": {"$nin": seen_obj_ids}
            })
            other_posts = await cursor_others.to_list(length=None)
            random.shuffle(other_posts)
            needed = 20 - len(posts)
            posts.extend(other_posts[:needed])

    else:
        cursor_others = posts_collection.find({
            "visibility": "public",
            "_id": {"$nin": seen_obj_ids}
        })
        other_posts = await cursor_others.to_list(length=None)
        random.shuffle(other_posts)
        posts = other_posts[:20]

    if not posts:
        return HTMLResponse("")  # Devuelve vacío si no quedan más posts

    # Actualizamos la sesión acumulando los nuevos posts vistos
    request.session["seen_posts"] = seen_posts + [str(p["_id"]) for p in posts]

    # Enriquecemos posts con username, profile_image y comentarios
    enriched_posts = []
    for post in posts:
        post_user = await users_collection.find_one({"_id": post["userId"]})
        if not post_user:
            continue

        post["username"] = post_user["username"]
        post["profile_image"] = post_user.get("profile_image")

        comment_objects = []
        for comment_id in post.get("comments", []):
            comment = await comments_collection.find_one({"_id": comment_id})
            if comment:
                comment_user = await users_collection.find_one({"_id": comment["userId"]})
                comment["username"] = comment_user["username"] if comment_user else "Usuario"
                comment["userId"] = str(comment["userId"])

                if "creationDate" in comment:
                    dt = comment["creationDate"]
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    comment["creationDateFormatted"] = dt.strftime("%H:%M %d/%m/%y")
                else:
                    comment["creationDateFormatted"] = ""
                comment_objects.append(comment)

        post["comment_objects"] = comment_objects
        post["likes_count"] = len(post.get("likes", []))

        enriched_posts.append(post)

    return templates.TemplateResponse(request, "feed_posts_partial.html", {
        "request": request,
        "posts": enriched_posts
    })

@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post(request: Request, post_id: str):
    user = request.session.get("user")
    
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de post inválido")
        
    post = await posts_collection.find_one({"_id": obj_id})
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
        
    # Verificar visibilidad
    if post.get("visibility") == "private":
        if not user:
            return RedirectResponse("/login", status_code=303)
            
        # Es privado, solo puede verlo el dueño o alguien que le sigue (o admin)
        if str(post["userId"]) != user["id"] and user.get("role") != "admin":
            user_data = await users_collection.find_one({"_id": ObjectId(user["id"])})
            following_ids = [str(uid) for uid in user_data.get("following", [])]
            if str(post["userId"]) not in following_ids:
                raise HTTPException(status_code=403, detail="Esta publicación es privada. Necesitas seguir al usuario para verla.")

    # Enriquecer el post
    post_user = await users_collection.find_one({"_id": post["userId"]})
    post["username"] = post_user["username"] if post_user else "Usuario"
    post["profile_image"] = post_user.get("profile_image")

    comment_objects = []
    for comment_id in post.get("comments", []):
        comment = await comments_collection.find_one({"_id": comment_id})
        if comment:
            comment_user = await users_collection.find_one({"_id": comment["userId"]})
            comment["username"] = comment_user["username"] if comment_user else "Usuario"
            comment["userId"] = str(comment["userId"])

            if "creationDate" in comment:
                dt = comment["creationDate"]
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                comment["creationDateFormatted"] = dt.strftime("%H:%M %d/%m/%y")
            else:
                comment["creationDateFormatted"] = ""
            comment_objects.append(comment)

    post["comment_objects"] = comment_objects
    post["likes_count"] = len(post.get("likes", []))
    post["_id"] = str(post["_id"])

    # Pasamos el post dentro de una lista para reutilizar feed_posts_partial.html
    return templates.TemplateResponse(request, "post_detail.html", {
        "request": request,
        "user": user,
        "posts": [post]
    })



@app.post("/change-role/{user_id}")
async def change_role(user_id: str, request: Request):
    current_user = request.session.get("user")
    
    # Validamos usando el campo 'role' que es el estándar seguro
    if not current_user or current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para realizar esta acción"
        )
    
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
    target_user = await users_collection.find_one({"_id": obj_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    current_role = target_user.get("role", "user")
    if current_role == "admin":
        new_role = "user"
    else:
        new_role = "admin"
    
    await users_collection.update_one({"_id": obj_id}, {"$set": {"role": new_role}})
    return {"status": "success", "new_role": new_role}

@app.post("/follow/{user_id}")
async def follow_user(user_id: str, request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    
    target_uid = str(user_id)
    current_uid = str(request.session["user"]["id"])
    
    if current_uid == target_uid:
        return RedirectResponse(url=f"/profile/{user_id}", status_code=303)
        
    # Guardamos en los arrays usando strings simples (tal y como lo tenías)
    await users_collection.update_one({"_id": ObjectId(current_uid)}, {"$addToSet": {"following": target_uid}})
    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"followers": current_uid}})
    
    return RedirectResponse(url=f"/profile/{user_id}", status_code=303)


@app.post("/unfollow/{user_id}")
async def unfollow_user(user_id: str, request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
        
    target_uid = str(user_id)
    current_uid = str(request.session["user"]["id"])
    
    # CORRECCIÓN AQUÍ: Ambos accesos por _id principal deben llevar ObjectId()
    await users_collection.update_one({"_id": ObjectId(current_uid)}, {"$pull": {"following": target_uid}})
    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$pull": {"followers": current_uid}})
    
    return RedirectResponse(url=f"/profile/{user_id}", status_code=303)