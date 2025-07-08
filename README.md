# VR Restaurant App

A virtual reality-themed restaurant web application powered by **Flask**, **Socket.IO**, and **SQLite**, allowing users to:

- Join VR dining rooms
- Place interactive food orders
- Customize dining environments
- Play mini-games while waiting
- View and manage kitchen orders
- Get real-time AI-powered food recommendations (via location)

##  Features

-  **Food Menu**: Order from appetizers, main courses, desserts, and drinks.
-  **Join Friends**: Enter a 6-digit room code to dine together.
-  **Environments**: Choose from 5 immersive VR themes.
-  **Mini-Games**: Includes memory, puzzle, trivia, and sushi slicing games.
-  **Kitchen Dashboard**: Monitor and complete pending orders.
-  **Live Recommendations**: AI chatbot uses Google Maps + OpenAI to suggest food nearby.

##  Tech Stack

- **Backend**: Flask, Flask-SocketIO
- **Frontend**: HTML, CSS, Vanilla JS
- **Database**: SQLite
- **APIs**: OpenAI, Google Maps
- **Others**: Jinja2, Python Dotenv

##  Project Structure

```plaintext
.
├── app.py                # Flask backend entry point
├── requirements.txt      # Python dependencies
├── static/               # Static assets (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
├── templates/            # Jinja2 HTML templates
│   ├── index.html
│   ├── menu.html
│   ├── kitchen.html
│   └── ...
├── instance/             # SQLite database (e.g., app.db)
├── .env                  # API keys and environment variables
└── README.md             # Project documentation
```

##  Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/Pragna-Sresta-5/VR-Mangement-System.git
   cd VR-Mangement-System
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your `.env` file with your OpenAI and Google Maps API keys.
4. Run the application:
   ```bash
   python app.py
   ```
5. Open your browser and go to `http://localhost:5000`.

##  Contributing

Contributions are welcome! Fork the repo and submit a pull request.

## 📄 License

This project is licensed under the repository's license.

---
