document.addEventListener("DOMContentLoaded", () => {
    const currentUser = window.currentUser || null;
    const postsContainer = document.getElementById("posts-container") || document.body;

    // ---------------------- DELEGACIÓN DE EVENTOS (LIKES / COMENTARIOS) ----------------------
    // Escuchamos los clics en el contenedor principal para que funcione en elementos viejos y nuevos
    postsContainer.addEventListener("click", async (e) => {
        
        // 1. LÓGICA DE LIKES / DISLIKES
        const likeBtn = e.target.closest(".like-btn");
        if (likeBtn) {
            if (likeBtn.dataset.busy === "true") return;
            likeBtn.dataset.busy = "true";

            const postId = likeBtn.dataset.postId;
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
            const postId = commentSubmitBtn.dataset.postId;
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
                if (commentData.creationDate) {
                    const dt = luxon.DateTime.fromISO(commentData.creationDate);
                    if (dt.isValid) {
                        formattedDate = dt.toFormat("HH:mm dd/LL/yy");
                    }
                }                

                const commentsDiv = document.querySelector(`#comments-${postId} .existing-comments`);
                if (commentsDiv) {
                    const newComment = document.createElement("div");
                    newComment.classList.add("comment");
                    newComment.id = `comment-${commentData._id || commentData.id}`;
                    newComment.innerHTML = `<b>${commentData.username || currentUser}</b>: ${commentData.text} <small>${formattedDate}</small>`;
                    commentsDiv.appendChild(newComment);
                }

                input.value = "";

                // Actualizar contador de comentarios
                const postCard = commentSubmitBtn.closest(".post-card");
                if (postCard) {
                    const commentBtn = postCard.querySelector(".comment-btn");
                    if (commentBtn) {
                        const countText = commentBtn.textContent.match(/\d+/);
                        if (countText) commentBtn.textContent = `💬 ${parseInt(countText[0]) + 1}`;
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
            const commentId = deleteCommentBtn.getAttribute("data-comment-id");
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

            const userId = followBtn.dataset.userId;
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

            if (data.location && locationEl) {
                locationEl.textContent = data.location;
            }

            if (data.time && timeEl) {
                const dt = luxon.DateTime.fromISO(data.time);
                if (dt.isValid) {
                    timeEl.textContent = `🕒 ${dt.toLocaleString(luxon.DateTime.TIME_SIMPLE)}`;
                } else {
                    timeEl.textContent = "🕒 --:--";
                }
            }

            if (data.weather && weatherEl) {
                weatherEl.textContent = `🌡 ${data.weather.temperature}°C, 🌬 ${data.weather.windspeed} km/h`;
            }
        } catch (err) {
            console.error("Error cargando info del navbar:", err);
        }
    }

    updateNavbarInfo();
    setInterval(updateNavbarInfo, 60000);

    // ---------------------- AUTOCOMPLETADO DE LOCALIDADES ----------------------
    const worldCapitals = [
        "Kabul","Tirana","Berlin","Andorra la Vella","Luanda","Saint John’s","Riyadh","Algiers","Buenos Aires","Yerevan",
        "Canberra","Vienna","Baku","Nassau","Dhaka","Bridgetown","Manama","Brussels","Belmopan","Porto-Novo",
        "Minsk","Brasília","Sofia","Ouagadougou","Gitega","Praia","Phnom Penh","Yaoundé","Ottawa","Bangui",
        "N'Djamena","Santiago","Beijing","Bogotá","Moroni","Kinshasa","Brazzaville","San José","Yamoussoukro","Zagreb",
        "Havana","Nicosia","Prague","Copenhagen","Djibouti","Roseau","Santo Dominican","Quito","Cairo","San Salvador",
        "Asmara","Tallinn","Mbabane","Addis Ababa","Suva","Helsinki","Paris","Libreville","Banjul","Tbilisi",
        "Accra","Athens","Saint George’s","Guatemala City","Conakry","Bissau","Georgetown","Port‑au‑Prince","Tegucigalpa","Budapest",
        "Reykjavik","New Delhi","Jakarta","Tehran","Baghdad","Dublin","Jerusalem","Rome","Kingston","Tokyo",
        "Amman","Astana","Nairobi","Tarawa","Pristina","Kuwait City","Bishkek","Vientiane","Riga","Beirut",
        "Maseru","Monrovia","Tripoli","Vaduz","Vilnius","Luxembourg","Antananarivo","Lilongwe","Kuala Lumpur","Malé",
        "Bamako","Valletta","Majuro","Nouakchott","Port Louis","Mexico City","Palikir","Chisinau","Monaco","Ulaanbaatar",
        "Podgorica","Rabat","Maputo","Naypyidaw","Windhoek","Yaren","Kathmandu","Amsterdam","Wellington","Managua",
        "Niamey","Abuja","Pyongyang","Oslo","Muscat","Islamabad","Melekeok","Panama City","Port Moresby","Asunción",
        "Lima","Manila","Warsaw","Lisbon","Doha","Bucharest","Moscow","Kigali","Basseterre","Castries","Kingstown",
        "Apia","San Marino","São Tomé","Abu Dhabi","Dakar","Belgrade","Victoria","Freetown","Singapore","Bratislava",
        "Ljubljana","Honiara","Mogadishu","Pretoria","Seoul","Juba","Madrid","Colombo","Khartoum","Paramaribo",
        "Stockholm","Bern","Damascus","Taipei","Dushanbe","Dodoma","Bangkok","Lomé","Nukuʻalofa","Port of Spain",
        "Tunis","Ankara","Ashgabat","Funafuti","Kampala","Kyiv","London","Washington, D.C.","Montevideo","Tashkent",
        "Port Vila","Vatican City","Caracas","Hanoi","Sana’a","Lusaka","Harare","Ramallah"
    ];

    const locationInput = document.getElementById("location");
    const resultsDiv = document.getElementById("location-results");

    if (locationInput && resultsDiv) {
        locationInput.addEventListener("input", () => {
            const query = locationInput.value.toLowerCase();
            resultsDiv.innerHTML = "";
            if (!query) return;

            const matches = worldCapitals.filter(capital => capital.toLowerCase().includes(query));

            matches.forEach(capital => {
                const div = document.createElement("div");
                div.textContent = capital;
                div.style.padding = "5px";
                div.style.cursor = "pointer";
                div.addEventListener("click", () => {
                    locationInput.value = capital;
                    resultsDiv.innerHTML = "";
                });
                resultsDiv.appendChild(div);
            });
        });

        document.addEventListener("click", e => {
            if (!resultsDiv.contains(e.target) && e.target !== locationInput) {
                resultsDiv.innerHTML = "";
            }
        });
    }

    // ---------------------- CAMBIAR ROLES DE USUARIO ----------------------
    const roleButtons = document.querySelectorAll(".btn-promote, .btn-demote");
    roleButtons.forEach(button => {
        button.addEventListener("click", async (e) => {
            e.preventDefault();
            const userId = button.getAttribute("data-user-id");
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

// ---------------------- NUEVO BOTÓN: CARGAR MÁS POSTS (SUSTITUYE AL SCROLL) ----------------------
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
