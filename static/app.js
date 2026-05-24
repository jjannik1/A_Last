document.addEventListener("DOMContentLoaded", () => {
    const currentUser = window.currentUser || null;
    const postsContainer = document.getElementById("posts-container") || document.body;

    // ---------------------- DELEGACIÓN DE EVENTOS PRINCIPAL ----------------------
    // Escuchamos todos los clics que ocurran dentro del contenedor de publicaciones.
    // Usamos delegación de eventos para que funcione incluso en las publicaciones que se
    // cargan dinámicamente más tarde (por ejemplo, al darle a 'Cargar más' o enviar un comentario nuevo).
    postsContainer.addEventListener("click", async (e) => {
        
        // 1. LÓGICA DE LIKES / DISLIKES
        const likeBtn = e.target.closest(".like-btn");
        if (likeBtn) {
            if (likeBtn.dataset.busy === "true") return;
            likeBtn.dataset.busy = "true";

            const postId = likeBtn.id.replace("like-btn-", "");
            const liked = likeBtn.classList.contains("liked");

            try {
                let res = await fetch(liked ? `/dislike/${postId}` : `/like/${postId}`, { method: "POST" });
                
                if (!res.ok) {
                    alert("Error al dar like/dislike. ¿Estás logueado?");
                    return;
                }

                const data = await res.json();
                const likesCountSpan = likeBtn.querySelector(".likes-count");
                if (likesCountSpan) likesCountSpan.textContent = data.likes_count;

                likeBtn.classList.toggle("liked", data.liked);
            } catch (err) {
                console.error(err);
            } finally {
                likeBtn.dataset.busy = "false";
            }
            return;
        }

        // 2. LÓGICA DE ENVÍO DE COMENTARIOS
        const commentSubmitBtn = e.target.closest(".comment-submit");
        if (commentSubmitBtn) {
            const postId = commentSubmitBtn.id.replace("comment-submit-", "");
            const input = commentSubmitBtn.closest(".new-comment").querySelector(".comment-input");
            const text = input.value.trim();
            if (!text) return;

            try {
                const data = new FormData();
                data.append("post_id", postId);
                data.append("text", text);

                const res = await fetch("/comment", { method: "POST", body: data });
                if (!res.ok) {
                    alert("Error al comentar. ¿Estás logueado?");
                    return;
                }

                const commentData = await res.json();

                let formattedDate = "";
                if (commentData.creationDate !== undefined && commentData.creationDate !== null) {
                    const dt = new Date(commentData.creationDate);
                    if (!isNaN(dt.getTime())) {
                        const hh = String(dt.getHours()).padStart(2, '0');
                        const mm = String(dt.getMinutes()).padStart(2, '0');
                        const dd = String(dt.getDate()).padStart(2, '0');
                        const mo = String(dt.getMonth() + 1).padStart(2, '0');
                        const yy = String(dt.getFullYear()).slice(-2);
                        formattedDate = hh + ":" + mm + " " + dd + "/" + mo + "/" + yy;
                    }
                }                

                const commentsDiv = document.querySelector(`#comments-${postId} .existing-comments`);
                if (commentsDiv !== null) {
                    const newComment = document.createElement("div");
                    newComment.classList.add("comment");
                    const newId = commentData._id || commentData.id;
                    newComment.id = "comment-" + newId;
                    newComment.innerHTML = "<b>" + (commentData.username || currentUser) + "</b>: " + commentData.text + " <small>" + formattedDate + "</small> <button id='delete-comment-" + newId + "' class='delete-comment-btn'><i class='fa-solid fa-trash'></i></button>";
                    commentsDiv.appendChild(newComment);
                }

                input.value = "";

                // Actualizar contador de comentarios
                const postCard = commentSubmitBtn.closest(".post-card");
                if (postCard) {
                    const commentBtn = postCard.querySelector(".comment-btn");
                    if (commentBtn) {
                        const countText = commentBtn.textContent.match(/\d+/);
                        if (countText) commentBtn.innerHTML = `<i class="fa-solid fa-comment"></i> ${parseInt(countText[0]) + 1}`;
                    }
                }

            } catch (err) {
                console.error(err);
            }
            return;
        }

        // 3. LÓGICA DE BORRAR COMENTARIO
        const deleteCommentBtn = e.target.closest(".delete-comment-btn");
        if (deleteCommentBtn) {
            const commentId = deleteCommentBtn.id.replace("delete-comment-", "");
            if (!commentId) return;

            try {
                const res = await fetch(`/delete-my-comment/${commentId}`, { method: "POST" });

                if (!res.ok) {
                    alert("No autorizado para borrar este comentario");
                    return;
                }

                const data = await res.json();

                if (data.success) {
                    const commentDiv = document.getElementById(`comment-${commentId}`);
                    if (commentDiv) commentDiv.remove();

                    const postDiv = deleteCommentBtn.closest(".post-card");
                    const commentBtn = postDiv.querySelector(".comment-btn");
                    if (commentBtn) {
                        const countText = commentBtn.textContent.match(/\d+/);
                        if (countText) commentBtn.textContent = `💬 ${parseInt(countText[0]) - 1}`;
                    }
                }

            } catch (err) {
                console.error("Error borrando comentario:", err);
            }
            return;
        }
    });

    // ---------------------- DELEGACIÓN DE EVENTOS FOLLOW / UNFOLLOW ----------------------
    document.addEventListener("click", async (e) => {
        const followBtn = e.target.closest(".follow-btn");
        if (followBtn) {
            e.preventDefault();
            if (followBtn.dataset.busy === "true") return;
            followBtn.dataset.busy = "true";

            const userId = followBtn.id.replace("follow-btn-", "");
            const isFollowing = followBtn.classList.contains("following");

            try {
                let res = await fetch(isFollowing ? `/unfollow/${userId}` : `/follow/${userId}`, { method: "POST" });
                
                if (!res.ok) {
                    alert("Error. ¿Estás logueado?");
                    return;
                }

                const data = await res.json();
                
                if (data.success) {
                    const followersCountDiv = document.getElementById("followers-count");
                    if (followersCountDiv) followersCountDiv.textContent = data.followers_count;

                    if (data.following) {
                        followBtn.classList.add("following");
                        followBtn.innerText = "Siguiendo ✓";
                        followBtn.style.background = "rgba(255,255,255,0.1)";
                        followBtn.style.color = "var(--text-main)";
                        followBtn.style.border = "1px solid var(--border)";
                        followBtn.className = "follow-btn following";
                        followBtn.onmouseover = function() { this.innerText='Dejar de seguir ❌'; this.style.background='var(--danger, #dc3545)'; this.style.color='white'; };
                        followBtn.onmouseout = function() { this.innerText='Siguiendo ✓'; this.style.background='rgba(255,255,255,0.1)'; this.style.color='var(--text-main)'; };
                    } else {
                        followBtn.classList.remove("following");
                        followBtn.innerText = "Seguir";
                        followBtn.className = "follow-btn btn-primary";
                        followBtn.style.padding = "10px 25px";
                        followBtn.style.borderRadius = "30px";
                        followBtn.style.fontWeight = "600";
                        followBtn.style.cursor = "pointer";
                        followBtn.style.border = "none";
                        followBtn.style.background = "";
                        followBtn.style.color = "";
                        followBtn.onmouseover = null;
                        followBtn.onmouseout = null;
                    }
                }
            } catch (err) {
                console.error(err);
            } finally {
                followBtn.dataset.busy = "false";
            }
        }
    });

    // ---------------------- TOGGLE COMENTARIOS ----------------------
    window.toggleComments = (postId) => {
        const div = document.getElementById(`comments-${postId}`);
        if (div) div.classList.toggle("hidden");
    };

    // ---------------------- NAVBAR: HORA + CLIMA ----------------------
    async function updateNavbarInfo() {
        try {
            const res = await fetch("/navbar-info");
            if (!res.ok) return;

            const data = await res.json();
            const timeEl = document.getElementById("time");
            const weatherEl = document.getElementById("weather");
            const locationEl = document.getElementById("user-location");

            if (data.location !== undefined && data.location !== null) {
                if (locationEl !== null) {
                    locationEl.innerHTML = '<i class="fa-solid fa-location-dot"></i> ' + data.location;
                }
            } else {
                if (locationEl !== null) {
                    locationEl.innerHTML = '<i class="fa-solid fa-location-dot"></i> Sin ubicación';
                }
            }

            if (data.time !== undefined && data.time !== null) {
                if (timeEl !== null) {
                    timeEl.innerHTML = '<i class="fa-regular fa-clock"></i> ' + data.time;
                }
            } else {
                if (timeEl !== null) {
                    timeEl.innerHTML = '<i class="fa-regular fa-clock"></i> --:--';
                }
            }

            if (data.weather !== undefined && data.weather !== null) {
                if (weatherEl !== null) {
                    weatherEl.innerHTML = '<i class="fa-solid fa-temperature-half"></i> ' + data.weather.temperature + "°C, <i class='fa-solid fa-wind'></i> " + data.weather.windspeed + " km/h";
                }
            } else {
                if (weatherEl !== null) {
                    weatherEl.innerHTML = '<i class="fa-solid fa-temperature-half"></i> --°C';
                }
            }
        } catch (err) {
            console.error("Error cargando info del navbar:", err);
        }
    }

    updateNavbarInfo();
    setInterval(updateNavbarInfo, 60000);


    // ---------------------- CAMBIAR ROLES DE USUARIO ----------------------
    const roleButtons = document.querySelectorAll(".btn-promote, .btn-demote");
    roleButtons.forEach(button => {
        button.addEventListener("click", async (e) => {
            e.preventDefault();
            let userId = "";
            if (button.id && button.id.startsWith("role-btn-")) {
                userId = button.id.replace("role-btn-", "");
            } else {
                userId = button.getAttribute("data-user-id"); // Por si acaso queda alguno viejo
            }
            try {
                const response = await fetch(`/change-role/${userId}`, { method: "POST" });
                if (response.ok) {
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    alert("Error: " + (errorData.detail || "No autorizado"));
                }
            } catch (error) {
                console.error("Error en la petición:", error);
                alert("Hubo un problema de red al cambiar el rol.");
            }
        });
    });
});

// ---------------------- PAGINACIÓN: CARGAR MÁS POSTS ----------------------
// Función que pide al backend el siguiente lote de publicaciones y las añade al final de la página.
document.addEventListener("DOMContentLoaded", () => {
    const loadMoreBtn = document.getElementById("load-more-btn");
    const postsContainer = document.getElementById("posts-container");
    let feedLoading = false;

    if (loadMoreBtn && postsContainer) {
        loadMoreBtn.addEventListener("click", async () => {
            if (feedLoading) return;
            feedLoading = true;
            
            loadMoreBtn.disabled = true;
            loadMoreBtn.textContent = "Cargando...";

            try {
                const res = await fetch("/feed/load-more");
                if (!res.ok) {
                    alert("Error al cargar más publicaciones.");
                    loadMoreBtn.disabled = false;
                    loadMoreBtn.textContent = "Cargar más publicaciones";
                    feedLoading = false;
                    return;
                }

                const html = await res.text();

                if (html.trim() === "") {
                    loadMoreBtn.textContent = "No hay más publicaciones";
                    loadMoreBtn.style.backgroundColor = "#cccccc";
                    loadMoreBtn.style.cursor = "not-allowed";
                    return;
                }

                // Inyectamos los posts al final del contenedor
                postsContainer.insertAdjacentHTML("beforeend", html);
                
                loadMoreBtn.disabled = false;
                loadMoreBtn.textContent = "Cargar más publicaciones";
            } catch (err) {
                console.error("Error cargando más posts:", err);
                loadMoreBtn.disabled = false;
                loadMoreBtn.textContent = "Cargar más publicaciones";
            }
            feedLoading = false;
        });
    }
});


// FUNCIONES GLOBALES DE ADMIN PERFIL
// Función para dar permisos de Administrador
function promoverUsuario(userId) {
    if (confirm("¿Estás seguro de que deseas hacer administrador a este usuario?")) {
        fetch(`/change-role/${userId}`, {
            method: 'POST'
        })
        .then(response => {
            if (response.ok) {
                window.location.reload(); // Recarga el perfil para ver el cambio
            } else {
                alert("Error al intentar promover al usuario.");
            }
        })
        .catch(error => console.error("Error:", error));
    }
}

// Función para quitar permisos de Administrador (Demote)
function degradarUsuario(userId) {
    if (confirm("¿Estás seguro de que deseas quitarle los permisos de administrador a este usuario?")) {
        fetch(`/change-role/${userId}`, {
            method: 'POST'
        })
        .then(response => {
            if (response.ok) {
                window.location.reload(); // Recarga el perfil para ver el cambio
            } else {
                alert("Error al intentar degradar al usuario.");
            }
        })
        .catch(error => console.error("Error:", error));
    }
}
