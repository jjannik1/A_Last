document.addEventListener("DOMContentLoaded", () => {
    const currentUser = window.currentUser || null;

    // ---------------------- LIKES / DISLIKES ----------------------
    document.querySelectorAll(".like-btn").forEach(btn => {
        let busy = false;
        btn.addEventListener("click", async () => {
            if (busy) return;
            busy = true;

            const postId = btn.dataset.postId;
            const liked = btn.classList.contains("liked");

            try {
                const res = await fetch(liked ? `/dislike/${postId}` : `/like/${postId}`, {
                    method: "POST"
                });
                if (!res.ok) {
                    alert("Error al dar like/deslike. ¿Estás logueado?");
                    busy = false;
                    return;
                }

                const data = await res.json();
                const likesCountSpan = btn.querySelector(".likes-count");
                if (likesCountSpan) likesCountSpan.textContent = data.likes_count;

                btn.classList.toggle("liked", data.liked);
            } catch (err) {
                console.error(err);
            }

            busy = false;
        });
    });

    // ---------------------- TOGGLE COMENTARIOS ----------------------
    window.toggleComments = (postId) => {
        const div = document.getElementById(`comments-${postId}`);
        if (div) div.classList.toggle("hidden");
    };

    // ---------------------- ENVÍO DE COMENTARIOS ----------------------
    document.querySelectorAll(".comment-submit").forEach(btn => {
        btn.addEventListener("click", async () => {
            const postId = btn.dataset.postId;
            const input = btn.closest(".new-comment").querySelector(".comment-input");
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
                    newComment.innerHTML = `<b>${commentData.username || currentUser }</b>: ${commentData.text} <small>${formattedDate}</small>`;
                    commentsDiv.appendChild(newComment);
                }

                input.value = "";

                // Actualizar contador de comentarios
                const commentBtn = document.querySelector(`.post-card #comments-${postId}`)?.previousElementSibling?.querySelector(".comment-btn");
                if (commentBtn) {
                    const countText = commentBtn.textContent.match(/\d+/);
                    if (countText) commentBtn.textContent = `💬 ${parseInt(countText[0]) + 1}`;
                }

            } catch (err) {
                console.error(err);
            }
        });
    });
    document.addEventListener("click", async (e) => {
    if (e.target.classList.contains("delete-comment-btn")) {
        const btn = e.target;
// ---------------------- BORRAR COMENTARIO ----------------------
    document.querySelectorAll(".delete-comment-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const commentId = btn.dataset.commentId;

            if (!commentId) return;

            try {
                const res = await fetch(`/delete-my-comment/${commentId}`, {
                    method: "POST"
                });

                if (!res.ok) {
                    alert("No autorizado para borrar este comentario");
                    return;
                }

                const data = await res.json();

                if (data.success) {
                    // Quitar comentario del DOM
                    const commentDiv = document.getElementById(`comment-${commentId}`);
                    if (commentDiv) commentDiv.remove();

                    // Actualizar contador de comentarios
                    const postDiv = btn.closest(".post-card");
                    const commentBtn = postDiv.querySelector(".comment-btn");
                    if (commentBtn) {
                        const countText = commentBtn.textContent.match(/\d+/);
                        if (countText) commentBtn.textContent = `💬 ${parseInt(countText[0]) - 1}`;
                    }
                }

            } catch (err) {
                console.error("Error borrando comentario:", err);
            }
        });
    });
        }
});

    // ---------------------- NAVBAR: HORA + CLIMA ----------------------
    async function updateNavbarInfo() {
        try {
            const res = await fetch("/navbar-info");
            if (!res.ok) return;

            const data = await res.json();
            const timeEl = document.getElementById("time");
            const weatherEl = document.getElementById("weather");
            const locationEl = document.getElementById("user-location");

                    // LOCALIDAD
            if (data.location && locationEl) {
                locationEl.textContent = data.location;
            }

            // HORA
            if (data.time) {
                const dt = luxon.DateTime.fromISO(data.time);
                if (dt.isValid) {
                    timeEl.textContent = `🕒 ${dt.toLocaleString(luxon.DateTime.TIME_SIMPLE)}`;
                } else {
                    timeEl.textContent = "🕒 --:--";
                }
            }

            // CLIMA
            if (data.weather) {
                // Ajustado a Open-Meteo: current_weather.temperature y windspeed
                if (weatherEl) weatherEl.textContent = `🌡 ${data.weather.temperature}°C, 🌬 ${data.weather.windspeed} km/h`;
            }
        } catch (err) {
            console.error("Error cargando info del navbar:", err);
        }
    }

    updateNavbarInfo();
    setInterval(updateNavbarInfo, 60000);


//const worldCapitals = [
//  "Kabul","Tirana","Algiers","Andorra la Vella","Luanda","Saint John's",
//  "Buenos Aires","Yerevan","Canberra","Vienna","Baku","Nassau",
//  "Manama","Dhaka","Bridgetown","Minsk","Brussels","Belmopan",
//  "Porto-Novo","Thimphu","La Paz","Sarajevo","Gaborone","Brasília",
//  "Sofia","Ouagadougou","Gitega","Praia","Phnom Penh","Yaoundé",
// "Ottawa","Bangui","N'Djamena","Santiago","Beijing","Bogotá",
//  "Moroni","Kinshasa","Brazzaville","San José","Yamoussoukro","Zagreb",
//  "Havana","Nicosia","Prague","Copenhagen","Djibouti","Roseau",
//  "Santo Domingo","Quito","Cairo","San Salvador","Malabo","Asmara",
//  "Tallin","Mbabane","Addis Ababa","Suva","Helsinki","Paris",
//  "Libreville","Banjul","Tbilisi","Berlin","Accra","Athens","Saint George's",
//  "Guatemala City","Conakry","Bissau","Georgetown","Port-au-Prince",
//  "Tegucigalpa","Budapest","Reykjavik","New Delhi","Jakarta","Tehran",
//  "Baghdad","Dublin","Jerusalem","Rome","Kingston","Tokyo","Amman",
//  "Nur-Sultan","Nairobi","Tarawa","Pristina","Kuwait City","Bishkek",
//  "Vientiane","Riga","Beirut","Maseru","Monrovia","Tripoli","Vaduz",
//  "Vilnius","Luxembourg","Antananarivo","Lilongwe","Kuala Lumpur",
//  "Malé","Bamako","Valletta","Majuro","Nouakchott","Port Louis",
//  "Mexico City","Palikir","Chisinau","Monaco","Ulaanbaatar","Podgorica",
//  "Rabat","Maputo","Naypyidaw","Windhoek","Yaren","Kathmandu",
//  "Amsterdam","Wellington","Managua","Niamey","Abuja","Pyongyang",
//  "Oslo","Muscat","Islamabad","Ngerulmud","Jerusalem","Panama City",
//  "Port Moresby","Asunción","Lima","Manila","Warsaw","Lisbon","Doha",
//  "Bucharest","Moscow","Kigali","Basseterre","Castries","Kingstown",
//  "Apia","San Marino","São Tomé","Riyadh","Dakar","Belgrade",
//  "Victoria","Freetown","Singapore","Bratislava","Ljubljana",
//  "Honiara","Mogadishu","Pretoria","Seoul","Juba","Madrid","Colombo",
//  "Khartoum","Paramaribo","Stockholm","Bern","Damascus","Taipei",
//  "Dushanbe","Dodoma","Bangkok","Lomé","Nukuʻalofa","Port of Spain",
//  "Tunis","Ankara","Ashgabat","Funafuti","Kampala","Kyiv","Abu Dhabi",
//  "London","Washington, D.C.","Montevideo","Tashkent","Port Vila",
//  "Vatican City","Caracas","Hanoi","Sana'a","Lusaka","Harare"
//];

const worldCapitals = [
  "Kabul","Tirana","Berlin","Andorra la Vella","Luanda",
  "Saint John’s","Riyadh","Algiers","Buenos Aires","Yerevan",
  "Canberra","Vienna","Baku","Nassau","Dhaka",
  "Bridgetown","Manama","Brussels","Belmopan","Porto-Novo",
  "Minsk","Brasília","Sofia","Ouagadougou","Gitega",
  "Praia","Phnom Penh","Yaoundé","Ottawa","Bangui",
  "N'Djamena","Santiago","Beijing","Bogotá","Moroni",
  "Kinshasa","Brazzaville","San José","Yamoussoukro","Zagreb",
  "Havana","Nicosia","Prague","Copenhagen","Djibouti",
  "Roseau","Santo Domingo","Quito","Cairo","San Salvador",
  "Asmara","Tallinn","Mbabane","Addis Ababa","Suva",
  "Helsinki","Paris","Libreville","Banjul","Tbilisi",
  "Accra","Athens","Saint George’s","Guatemala City","Conakry",
  "Bissau","Georgetown","Port‑au‑Prince","Tegucigalpa","Budapest",
  "Reykjavik","New Delhi","Jakarta","Tehran","Baghdad",
  "Dublin","Jerusalem","Rome","Kingston","Tokyo",
  "Amman","Astana","Nairobi","Tarawa","Pristina",
  "Kuwait City","Bishkek","Vientiane","Riga","Beirut",
  "Maseru","Monrovia","Tripoli","Vaduz","Vilnius",
  "Luxembourg","Antananarivo","Lilongwe","Kuala Lumpur","Malé",
  "Bamako","Valletta","Majuro","Nouakchott","Port Louis",
  "Mexico City","Palikir","Chisinau","Monaco","Ulaanbaatar",
  "Podgorica","Rabat","Maputo","Naypyidaw","Windhoek",
  "Yaren","Kathmandu","Amsterdam","Wellington","Managua",
  "Niamey","Abuja","Pyongyang","Oslo","Muscat",
  "Islamabad","Melekeok","Panama City","Port Moresby","Asunción",
  "Lima","Manila","Warsaw","Lisbon","Doha",
  "Bucharest","Moscow","Kigali","Basseterre","Castries",
  "Kingstown","Apia","San Marino","São Tomé","Abu Dhabi",
  "Dakar","Belgrade","Victoria","Freetown","Singapore",
  "Bratislava","Ljubljana","Honiara","Mogadishu","Pretoria",
  "Seoul","Juba","Madrid","Colombo","Khartoum",
  "Paramaribo","Stockholm","Bern","Damascus","Taipei",
  "Dushanbe","Dodoma","Bangkok","Lomé","Nukuʻalofa",
  "Port of Spain","Tunis","Ankara","Ashgabat","Funafuti",
  "Kampala","Kyiv","London","Washington, D.C.","Montevideo",
  "Tashkent","Port Vila","Vatican City","Caracas","Hanoi",
  "Sana’a","Lusaka","Harare","Ramallah"
];


const locationInput = document.getElementById("location");
const resultsDiv = document.getElementById("location-results");

locationInput.addEventListener("input", () => {
    const query = locationInput.value.toLowerCase();
    resultsDiv.innerHTML = "";
    if (!query) return;

    const matches = worldCapitals.filter(capital =>
        capital.toLowerCase().includes(query)
    );

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

// Cerrar resultados al hacer click fuera
document.addEventListener("click", e => {
    if (resultsDiv && locationInput) {  // <-- make sure they exist
        if (!resultsDiv.contains(e.target) && e.target !== locationInput) {
            resultsDiv.innerHTML = "";
        }
    }
});

});

// ---------------------- FEED: CARGAR MÁS POSTS ----------------------
document.addEventListener("DOMContentLoaded", () => {
    const feedContainer = document.querySelector("body"); // o un contenedor específico si lo quieres
    let feedLoading = false;

    async function loadMorePosts() {
        if (feedLoading) return;
        feedLoading = true;

        try {
            const res = await fetch("/feed/load-more"); // Endpoint AJAX que vamos a crear
            if (!res.ok) {
                console.error("Error cargando más posts");
                feedLoading = false;
                return;
            }

            const html = await res.text();

            // Insertamos los nuevos posts al final del feed
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = html;

            const newPosts = tempDiv.querySelectorAll(".post-card");
            if (newPosts.length === 0) {
                console.log("No hay más posts disponibles");
            }

            newPosts.forEach(post => feedContainer.appendChild(post));
        } catch (err) {
            console.error("Error cargando más posts:", err);
        }

        feedLoading = false;
    }

    // Scroll infinito: cargar más posts cuando llegamos al fondo
    window.addEventListener("scroll", () => {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) {
            loadMorePosts();
        }
    });
});

let currentChatUser = null;
let lastTimestamp = null;

async function loadChat(userId) {

    currentChatUser = userId;

    try {

        const res = await fetch(
            `/api/chat/history/${userId}`
        );

        const messages = await res.json();

        const chatBox = document.getElementById("chat-box");

        chatBox.innerHTML = "";

        messages.forEach(msg => {
            appendMessage(msg);
        });

        // Guardar último timestamp
        if (messages.length > 0) {
            lastTimestamp =
                messages[messages.length - 1].timestamp;
        }

    } catch(err) {
        console.error(err);
    }
}

async function loadNewMessages() {

    if (!currentChatUser) return;

    try {

        let url =
            `/api/chat/history/${currentChatUser}`;

        if (lastTimestamp) {
            url += `?after=${lastTimestamp}`;
        }

        const res = await fetch(url);

        const messages = await res.json();

        if (messages.length > 0) {

            messages.forEach(msg => {
                appendMessage(msg);
            });

            lastTimestamp =
                messages[messages.length - 1].timestamp;
        }

    } catch(err) {
        console.error(err);
    }
}
setInterval(loadNewMessages, 3000);

function appendMessage(msg) {

    const chatBox = document.getElementById("chat-box");

    const div = document.createElement("div");

    div.classList.add("message");

    if (msg.sender_id === window.currentUserId) {
        div.classList.add("my-message");
    } else {
        div.classList.add("other-message");
    }

    div.innerHTML = `
        <p>${msg.content}</p>
        <small>${msg.timestamp}</small>
    `;

    chatBox.appendChild(div);

    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {

    const input = document.getElementById("message-input");

    const content = input.value.trim();

    if (!content || !currentChatUser) return;

    try {

        const res = await fetch(
            "/api/chat/send",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    receiver_id: currentChatUser,
                    content: content
                })
            }
        );

        const msg = await res.json();


        lastTimestamp = msg.timestamp;

        input.value = "";

    } catch(err) {
        console.error(err);
    }
}

document
    .getElementById("send-btn")
    .addEventListener("click", sendMessage);

