if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(success, error);
} else {
    document.getElementById("status").innerText = "Geolocation not supported.";
}

function success(position) {
    const lat = position.coords.latitude;
    const lng = position.coords.longitude;

    fetch(`/recommendations?lat=${lat}&lng=${lng}`)
        .then(res => res.json())
        .then(data => {
            const status = document.getElementById("status");
            const chat = document.getElementById("chat");

            if (data.error) {
                status.innerText = data.error;
                return;
            }

            status.innerText = "Here's an AI-powered food recommendation:";

            // Add AI message
            const aiMsg = document.createElement("div");
            aiMsg.className = "bot";
            aiMsg.innerHTML = `<strong>🤖 Bot:</strong><br>${data.ai_recommendation}`;
            chat.appendChild(aiMsg);

            // Optional: Show all places
            const placesMsg = document.createElement("div");
            placesMsg.className = "bot";
            placesMsg.innerHTML = "<strong>All nearby places:</strong><br>" +
                data.places.map(p => `${p.name} ⭐ ${p.rating} — ${p.address}`).join("<br>");
            chat.appendChild(placesMsg);
        });
}

function error() {
    document.getElementById("status").innerText = "Unable to retrieve your location.";
}