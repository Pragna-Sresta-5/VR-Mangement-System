# ===== SIMPLE VR RESTAURANT APP =====
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import random
import string
import json
import time
from datetime import datetime
import threading
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vr_restaurant_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== DATABASE SETUP =====
def init_database():
    try:
        conn = sqlite3.connect('vr_restaurant.db')
        cursor = conn.cursor()
        
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT NOT NULL,
                items TEXT NOT NULL,
                total_price REAL NOT NULL,
                status TEXT DEFAULT 'preparing',
                order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                room_code TEXT PRIMARY KEY,
                environment TEXT DEFAULT 'beach',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Menu items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT
            )
        ''')
        
        # Insert simplified menu items (only 8 items total)
        sample_items = [
            ('Caesar Salad', 'appetizers', 12.99, 'Fresh romaine lettuce with parmesan'),
            ('Chicken Wings', 'appetizers', 14.99, 'Spicy buffalo wings with blue cheese'),
            ('Grilled Salmon', 'main_courses', 28.99, 'Atlantic salmon with lemon herbs'),
            ('Chicken Pasta', 'main_courses', 18.99, 'Creamy alfredo with grilled chicken'),
            ('Chocolate Cake', 'desserts', 8.99, 'Rich chocolate layer cake'),
            ('Ice Cream', 'desserts', 6.99, 'Vanilla, chocolate, or strawberry'),
            ('Craft Beer', 'drinks', 6.99, 'Local brewery selection'),
            ('Soda', 'drinks', 3.99, 'Coke, Pepsi, Sprite')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO menu_items (name, category, price, description)
            VALUES (?, ?, ?, ?)
        ''', sample_items)
        
        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

# ===== VR RESTAURANT MANAGER CLASS =====
class VRRestaurantManager:
    def __init__(self):
        self.active_rooms = {}
        self.environments = [
            {'id': 'beach', 'name': 'Beach Sunset'},
            {'id': 'rooftop', 'name': 'Rooftop Sky'},
            {'id': 'zen', 'name': 'Zen Garden'},
            {'id': 'space', 'name': 'Space Station'},
            {'id': 'jungle', 'name': 'Jungle Cafe'}
        ]
        
    def generate_room_code(self):
        return ''.join(random.choices(string.digits, k=6))
    
    def create_room(self):
        room_code = self.generate_room_code()
        while room_code in self.active_rooms:
            room_code = self.generate_room_code()
        
        self.active_rooms[room_code] = {
            'users': [],
            'environment': 'beach',
            'current_order': []
        }
        
        # Save to database
        try:
            conn = sqlite3.connect('vr_restaurant.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO rooms (room_code) VALUES (?)', (room_code,))
            conn.commit()
        except Exception as e:
            print(f"Error creating room: {e}")
        finally:
            conn.close()
        
        return room_code
    
    def join_room(self, room_code, user_id):
        if room_code in self.active_rooms:
            if user_id not in self.active_rooms[room_code]['users']:
                self.active_rooms[room_code]['users'].append(user_id)
            return True
        return False
    
    def get_menu_items(self, category=None):
        try:
            conn = sqlite3.connect('vr_restaurant.db')
            cursor = conn.cursor()
            
            if category:
                cursor.execute('SELECT * FROM menu_items WHERE category = ?', (category,))
            else:
                cursor.execute('SELECT * FROM menu_items')
            
            items = cursor.fetchall()
            return [{'id': item[0], 'name': item[1], 'category': item[2], 
                    'price': item[3], 'description': item[4]} for item in items]
        except Exception as e:
            print(f"Error getting menu items: {e}")
            return []
        finally:
            conn.close()

restaurant_manager = VRRestaurantManager()

# ===== ROUTES =====
@app.route('/')
def index():
    room_code = restaurant_manager.create_room()
    session['room_code'] = room_code
    return render_template('index.html', room_code=room_code)

@app.route('/join/<room_code>')
def join_room_page(room_code):
    if restaurant_manager.join_room(room_code, session.get('user_id', 'anonymous')):
        session['room_code'] = room_code
        return render_template('index.html', room_code=room_code)
    else:
        return "Room not found", 404

@app.route('/api/menu')
def get_menu():
    category = request.args.get('category')
    items = restaurant_manager.get_menu_items(category)
    return jsonify(items)

@app.route('/api/environments')
def get_environments():
    return jsonify(restaurant_manager.environments)

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.json
    room_code = session.get('room_code')
    
    if not room_code:
        return jsonify({'error': 'No room code'}), 400
    
    try:
        # Save order to database
        conn = sqlite3.connect('vr_restaurant.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (room_code, items, total_price)
            VALUES (?, ?, ?)
        ''', (room_code, json.dumps(data['items']), data['total_price']))
        order_id = cursor.lastrowid
        conn.commit()
        
        # Notify kitchen
        socketio.emit('new_order', {
            'order_id': order_id,
            'room_code': room_code,
            'items': data['items'],
            'total_price': data['total_price']
        }, room='kitchen')
        
        # Start cooking timer (simulate)
        cooking_time = random.randint(30, 90)  # 30-90 seconds for demo
        threading.Timer(cooking_time, notify_order_ready, [room_code, order_id]).start()
        
        return jsonify({'success': True, 'order_id': order_id, 'estimated_time': cooking_time})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

def notify_order_ready(room_code, order_id):
    try:
        # Update order status
        conn = sqlite3.connect('vr_restaurant.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', ('ready', order_id))
        conn.commit()
        
        # Notify VR clients
        socketio.emit('order_ready', {
            'order_id': order_id,
            'message': 'Your food is ready!'
        }, room=room_code)
    except Exception as e:
        print(f"Error notifying order ready: {e}")
    finally:
        conn.close()

# ===== SOCKET EVENTS =====
@socketio.on('connect')
def on_connect():
    print(f'User connected: {request.sid}')

@socketio.on('join_vr_room')
def on_join_room(data):
    room_code = data['room_code']
    join_room(room_code)
    emit('joined_room', {'room_code': room_code})

@socketio.on('change_environment')
def on_change_environment(data):
    room_code = session.get('room_code')
    if room_code in restaurant_manager.active_rooms:
        restaurant_manager.active_rooms[room_code]['environment'] = data['environment']
        emit('environment_changed', data, room=room_code)

@socketio.on('start_game')
def on_start_game(data):
    room_code = session.get('room_code')
    emit('game_started', data, room=room_code)

@socketio.on('join_kitchen')
def on_join_kitchen():
    join_room('kitchen')
    emit('kitchen_joined')

# ===== MINI GAMES =====
@app.route('/api/start_game/<game_type>')
def start_game(game_type):
    games = {
        'memory': {'type': 'memory', 'sequence': [1,2,3,4], 'max_score': 500},
        'puzzle': {'type': 'puzzle', 'pieces': list(range(1,17)), 'max_score': 250},
        'sushi_slice': {'type': 'sushi_slice', 'targets': 20, 'max_score': 400},
        'trivia': {'type': 'trivia', 'questions': 3, 'max_score': 300}
    }
    
    if game_type in games:
        return jsonify(games[game_type])
    return jsonify({'error': 'Game not found'}), 404

# ===== KITCHEN DASHBOARD =====
@app.route('/kitchen')
def kitchen_dashboard():
    return render_template('kitchen.html')

@app.route('/api/kitchen/orders')
def get_kitchen_orders():
    try:
        conn = sqlite3.connect('vr_restaurant.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, room_code, items, total_price, status, order_time
            FROM orders WHERE status IN ('preparing', 'ready')
            ORDER BY order_time ASC
        ''')
        orders = cursor.fetchall()
        return jsonify([{
            'id': order[0],
            'room_code': order[1],
            'items': json.loads(order[2]),
            'total_price': order[3],
            'status': order[4],
            'order_time': order[5]
        } for order in orders])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/kitchen/complete_order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    try:
        conn = sqlite3.connect('vr_restaurant.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', ('completed', order_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ===== HTML TEMPLATES =====
index_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VR Restaurant</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: white; border: 1px solid #ddd; }
        .room-code { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .main-menu { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .menu-card { 
            background: white; 
            padding: 30px; 
            text-align: center; 
            cursor: pointer;
            border: 1px solid #ddd;
        }
        .menu-card:hover { background: #f5f5f5; }
        .panel { 
            display: none; 
            background: white; 
            padding: 30px; 
            margin-top: 20px;
            border: 1px solid #ddd;
        }
        .panel.active { display: block; }
        .food-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .food-item { 
            background: white; 
            padding: 15px; 
            border: 1px solid #ddd;
        }
        .food-item h4 { margin-bottom: 5px; }
        .food-item p { margin: 5px 0; font-size: 14px; }
        .price { font-weight: bold; }
        button { 
            padding: 10px 20px; 
            border: 1px solid #333; 
            background: white; 
            cursor: pointer;
            margin: 5px;
        }
        button:hover { background: #f0f0f0; }
        .back-btn { border: 1px solid #666; }
        .environment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .game-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .game-card { 
            background: white; 
            padding: 20px; 
            text-align: center; 
            cursor: pointer;
            border: 1px solid #ddd;
        }
        .game-card:hover { background: #f5f5f5; }
        .order-summary { 
            background: #f5f5f5; 
            padding: 20px; 
            margin-top: 20px;
            border: 1px solid #ddd;
        }
        .notification { 
            position: fixed; 
            top: 50%; 
            left: 50%; 
            transform: translate(-50%, -50%); 
            background: white; 
            padding: 30px; 
            text-align: center; 
            display: none; 
            border: 2px solid #333;
            z-index: 1000;
        }
        input { padding: 10px; margin: 5px; border: 1px solid #ddd; }
        .category-buttons { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>VR Restaurant</h1>
            <div class="room-code">Room Code: <span id="roomCode">{{ room_code }}</span></div>
        </div>

        <!-- Main Menu -->
        <div id="mainMenu" class="main-menu">
            <div class="menu-card" onclick="showPanel('menuPanel')">
                <h3>Order Food</h3>
                <p>Browse menu and place orders</p>
            </div>
            <div class="menu-card" onclick="showPanel('environmentPanel')">
                <h3>Environment</h3>
                <p>Change dining atmosphere</p>
            </div>
            <div class="menu-card" onclick="showPanel('gamesPanel')">
                <h3>Games</h3>
                <p>Play while you wait</p>
            </div>
            <div class="menu-card" onclick="showPanel('friendsPanel')">
                <h3>Friends</h3>
                <p>Invite or join friends</p>
            </div>
        </div>

        <!-- Food Menu Panel -->
        <div id="menuPanel" class="panel">
            <h2>Restaurant Menu</h2>
            <button class="back-btn" onclick="showMainMenu()">Back</button>
            
            <div class="category-buttons">
                <button onclick="loadMenu('appetizers')">Appetizers</button>
                <button onclick="loadMenu('main_courses')">Main Courses</button>
                <button onclick="loadMenu('desserts')">Desserts</button>
                <button onclick="loadMenu('drinks')">Drinks</button>
            </div>
            
            <div id="foodGrid" class="food-grid"></div>
            
            <div class="order-summary">
                <h3>Current Order</h3>
                <div id="orderItems"></div>
                <div id="orderTotal">Total: $0.00</div>
                <button onclick="placeOrder()">Place Order</button>
            </div>
        </div>

        <!-- Environment Panel -->
        <div id="environmentPanel" class="panel">
            <h2>Choose Environment</h2>
            <button class="back-btn" onclick="showMainMenu()">Back</button>
            <div id="environmentGrid" class="environment-grid"></div>
        </div>

        <!-- Games Panel -->
        <div id="gamesPanel" class="panel">
            <h2>Mini-Games</h2>
            <button class="back-btn" onclick="showMainMenu()">Back</button>
            <div class="game-grid">
                <div class="game-card" onclick="startGame('memory')">
                    <h3>Memory Game</h3>
                    <p>Test your memory</p>
                </div>
                <div class="game-card" onclick="startGame('puzzle')">
                    <h3>Puzzle</h3>
                    <p>Solve the puzzle</p>
                </div>
                <div class="game-card" onclick="startGame('sushi_slice')">
                    <h3>Sushi Slice</h3>
                    <p>Slice the sushi</p>
                </div>
                <div class="game-card" onclick="startGame('trivia')">
                    <h3>Food Trivia</h3>
                    <p>Test your knowledge</p>
                </div>
            </div>
            <div id="gameArea"></div>
        </div>

        <!-- Friends Panel -->
        <div id="friendsPanel" class="panel">
            <h2>Friends</h2>
            <button class="back-btn" onclick="showMainMenu()">Back</button>
            <p>Share room code: <strong>{{ room_code }}</strong></p>
            <button onclick="copyRoomCode()">Copy Code</button>
            
            <div style="margin-top: 30px;">
                <h3>Join Room</h3>
                <input type="text" id="joinCodeInput" placeholder="Enter 6-digit code" maxlength="6">
                <button onclick="joinRoom()">Join</button>
            </div>
        </div>
    </div>

    <!-- Notification -->
    <div id="notification" class="notification">
        <h3 id="notificationTitle">Order Ready</h3>
        <p id="notificationText">Your food is ready!</p>
        <button onclick="hideNotification()">OK</button>
    </div>

    <script>
        const socket = io();
        let currentOrder = [];
        let orderTotal = 0;

        // Socket events
        socket.on('connect', function() {
            socket.emit('join_vr_room', {room_code: '{{ room_code }}'});
        });

        socket.on('order_ready', function(data) {
            showNotification('Order Ready', data.message);
        });

        // UI Functions
        function showPanel(panelId) {
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById('mainMenu').style.display = 'none';
            document.getElementById(panelId).classList.add('active');
        }

        function showMainMenu() {
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById('mainMenu').style.display = 'grid';
        }

        // Menu Functions
        async function loadMenu(category) {
            const response = await fetch(`/api/menu?category=${category}`);
            const items = await response.json();
            
            const grid = document.getElementById('foodGrid');
            grid.innerHTML = items.map(item => `
                <div class="food-item">
                    <h4>${item.name}</h4>
                    <p>${item.description}</p>
                    <p class="price">$${item.price}</p>
                    <button onclick="addToOrder('${item.name}', ${item.price})">Add</button>
                </div>
            `).join('');
        }

        function addToOrder(name, price) {
            currentOrder.push({name, price});
            orderTotal += price;
            updateOrderDisplay();
        }

        function updateOrderDisplay() {
            document.getElementById('orderItems').innerHTML = currentOrder.map(item => 
                `<div>${item.name} - $${item.price}</div>`
            ).join('');
            document.getElementById('orderTotal').textContent = `Total: $${orderTotal.toFixed(2)}`;
        }

        async function placeOrder() {
            if (currentOrder.length === 0) {
                alert('Add items first');
                return;
            }

            const response = await fetch('/api/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    items: currentOrder,
                    total_price: orderTotal
                })
            });

            if (response.ok) {
                const result = await response.json();
                alert(`Order placed! Estimated time: ${result.estimated_time} seconds`);
                currentOrder = [];
                orderTotal = 0;
                updateOrderDisplay();
                showMainMenu();
            }
        }

        // Environment Functions
        async function loadEnvironments() {
            const response = await fetch('/api/environments');
            const environments = await response.json();
            
            const grid = document.getElementById('environmentGrid');
            grid.innerHTML = environments.map(env => `
                <button onclick="changeEnvironment('${env.id}')">
                    ${env.name}
                </button>
            `).join('');
        }

        function changeEnvironment(envId) {
            socket.emit('change_environment', {environment: envId});
            alert('Environment changed');
            showMainMenu();
        }

        // Game Functions
        async function startGame(gameType) {
            const response = await fetch(`/api/start_game/${gameType}`);
            const gameData = await response.json();
            
            const gameArea = document.getElementById('gameArea');
            gameArea.innerHTML = `
                <div style="border: 1px solid #ddd; padding: 20px; margin-top: 20px;">
                    <h3>${gameType} Game Started</h3>
                    <p>Max score: ${gameData.max_score}</p>
                    <div id="gameScore">Score: 0</div>
                    <button onclick="simulateGame(${gameData.max_score})">Play</button>
                </div>
            `;
        }

        function simulateGame(maxScore) {
            let score = 0;
            const interval = setInterval(() => {
                score += Math.floor(Math.random() * 50) + 10;
                document.getElementById('gameScore').textContent = `Score: ${score}`;
                
                if (score >= maxScore * 0.8) {
                    clearInterval(interval);
                    document.getElementById('gameScore').textContent = `Final Score: ${score}`;
                }
            }, 500);
        }

        // Friends Functions
        function copyRoomCode() {
            navigator.clipboard.writeText('{{ room_code }}');
            alert('Code copied');
        }

        function joinRoom() {
            const code = document.getElementById('joinCodeInput').value;
            if (code.length === 6) {
                window.location.href = `/join/${code}`;
            } else {
                alert('Enter valid 6-digit code');
            }
        }

        // Notification Functions
        function showNotification(title, text) {
            document.getElementById('notificationTitle').textContent = title;
            document.getElementById('notificationText').textContent = text;
            document.getElementById('notification').style.display = 'block';
        }

        function hideNotification() {
            document.getElementById('notification').style.display = 'none';
        }

        // Initialize
        loadEnvironments();
        loadMenu('appetizers');
    </script>
</body>
</html>
'''

kitchen_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kitchen Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f9f9f9; }
        .header { background: white; padding: 20px; margin-bottom: 20px; border: 1px solid #ddd; }
        .orders-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .order-card { 
            background: white; 
            padding: 20px; 
            border: 1px solid #ddd;
        }
        .order-items { margin: 10px 0; }
        .order-item { background: #f5f5f5; padding: 5px 10px; margin: 5px 0; }
        button { 
            padding: 10px 20px; 
            border: 1px solid #333; 
            background: white; 
            cursor: pointer;
        }
        button:hover { background: #f0f0f0; }
        .status { font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Kitchen Dashboard</h1>
        <p>Manage VR restaurant orders</p>
    </div>

    <div id="ordersContainer" class="orders-grid"></div>

    <script>
        const socket = io();

        socket.on('connect', function() {
            socket.emit('join_kitchen');
            loadOrders();
        });

        socket.on('new_order', function(data) {
            loadOrders();
        });

        async function loadOrders() {
            const response = await fetch('/api/kitchen/orders');
            const orders = await response.json();
            
            const container = document.getElementById('ordersContainer');
            container.innerHTML = orders.map(order => `
                <div class="order-card">
                    <h3>Room: ${order.room_code}</h3>
                    <p class="status">Status: ${order.status}</p>
                    <p><strong>Total: $${order.total_price.toFixed(2)}</strong></p>
                    <p>Time: ${new Date(order.order_time).toLocaleTimeString()}</p>
                    
                    <div class="order-items">
                        <strong>Items:</strong>
                        ${order.items.map(item => `
                            <div class="order-item">${item.name} - $${item.price.toFixed(2)}</div>
                        `).join('')}
                    </div>
                    
                    ${order.status === 'preparing' ? `
                        <button onclick="completeOrder(${order.id})">Mark Ready</button>
                    ` : '<p>Ready for pickup</p>'}
                </div>
            `).join('');
        }

        async function completeOrder(orderId) {
            const response = await fetch(`/api/kitchen/complete_order/${orderId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                loadOrders();
            }
        }

        setInterval(loadOrders, 30000);
    </script>
</body>
</html>
'''

# ===== MAIN APPLICATION SETUP =====
if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Create template files
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    with open('templates/index.html', 'w') as f:
        f.write(index_template)
    
    with open('templates/kitchen.html', 'w') as f:
        f.write(kitchen_template)
    
    print("VR Restaurant App Starting...")
    print("Main App: http://localhost:5000")
    print("Kitchen: http://localhost:5000/kitchen")
    
    # Run the application
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)