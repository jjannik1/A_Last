# Manual Técnico - SocialApp

## Arquitectura del Sistema
SocialApp es una aplicación web renderizada en el servidor (SSR) que sigue una arquitectura monolítica con un cliente ligero.

*   **Backend**: Python 3.12+ utilizando el framework FastAPI.
*   **Base de Datos**: MongoDB (NoSQL).
*   **Frontend**: HTML5, CSS3, y Vanilla JavaScript. Las vistas se procesan mediante el motor de plantillas Jinja2.
*   **Infraestructura**: Despliegue orientado a contenedores mediante Docker Compose, servido a través de un proxy inverso Nginx con certificados SSL (`cert-public.pem`).

---

## Dependencias y Librerías (Backend)

El núcleo del backend se encuentra en `app/main.py`. A continuación se detallan las librerías principales:

### 1. FastAPI (`fastapi`)
Framework web principal y enrutador. Maneja las peticiones HTTP, el despacho de endpoints, e inyección de dependencias. Se utiliza por su alto rendimiento asíncrono y simplicidad en la definición de rutas (`@app.get`, `@app.post`).

### 2. Motor (`motor.motor_asyncio`)
Driver oficial asíncrono de MongoDB para Python. Permite operaciones I/O no bloqueantes en la base de datos, lo que es vital en aplicaciones FastAPI. Se utiliza para colecciones como `users_collection` y `posts_collection` mediante llamadas `await`.

### 3. Uvicorn (`uvicorn`)
El servidor web ASGI (Asynchronous Server Gateway Interface) empleado para ejecutar la aplicación FastAPI y hacer puente hacia Nginx.

### 4. Jinja2 (`fastapi.templating.Jinja2Templates`)
El motor de plantillas de Python. Permite la inyección dinámica de datos del backend (como variables de sesión de usuario y posts) directamente en los archivos `.html` de la carpeta `templates/` antes de servirlos al cliente.

### 5. Passlib (`passlib.hash.pbkdf2_sha256`)
Librería de seguridad de hashing. Todas las contraseñas se encriptan antes de almacenarse en MongoDB. Utiliza el algoritmo `pbkdf2_sha256` para garantizar que no haya texto plano en la base de datos, vital contra brechas de seguridad.

### 6. Starlette Middleware (`starlette.middleware.sessions`)
Encargado de la persistencia de sesiones seguras. Genera cookies encriptadas (gracias a un `secret_key`) para mantener el estado de login del usuario mientras navega entre distintas páginas de la red social.

### 7. HTTPX (`httpx`)
Cliente HTTP asíncrono utilizado en el servidor. En la ruta `/navbar-info`, permite hacer llamadas concurrentes a APIs externas (GeoJS para IP-localidad y Open-Meteo para datos climáticos) sin congelar el hilo principal del servidor de FastAPI.

### 8. Utilidades Estándar de Python
*   **`os` y `shutil`**: Gestión del sistema de archivos, creación de las rutas estáticas (`static/uploads/`) y el guardado seguro en disco de las subidas binarias de fotos de perfil y vídeos.
*   **`datetime`**: Generación de *timestamps* universales para posts, y prefijos para evitar colisiones de nombres de archivos (`YYMMDDHHMMSS-nombre.jpg`).
*   **`bson.ObjectId`**: Conversión y manejo de los IDs únicos de 24 caracteres hexadecimales de MongoDB.

---

## Lógica Interna del Cliente (Frontend)

El archivo `static/app.js` maneja la reactividad en el navegador del usuario utilizando Vanilla JS moderno.

### Delegación de Eventos
En lugar de asignar eventos estáticos (`onclick`) a botones individuales que puedan aparecer o desaparecer (debido a carga asíncrona), SocialApp utiliza **Delegación de Eventos**. 
Se adjunta un único `EventListener` al `document` o al contenedor principal (`posts-container`). Este listener intercepta los clics (`e.target`) e identifica si corresponden a un botón de "Like", un "Borrar Comentario" o un "Follow", disparando el comportamiento correspondiente.

### Peticiones Fetch Asíncronas (AJAX)
Las acciones críticas como los "Me Gusta", los "Follows", borrar comentarios, y la obtención del clima (`updateNavbarInfo`) se realizan de manera silenciosa en segundo plano usando `fetch()`. Esto permite actualizar partes del DOM dinámicamente sin que el usuario sufra recargas molestas de la página, ofreciendo una sensación parecida a una SPA (Single Page Application).
