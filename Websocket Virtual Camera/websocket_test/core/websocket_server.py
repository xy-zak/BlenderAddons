import bpy
import threading
import json
import asyncio
import websockets
from bpy.app import timers

# Global variables
websocket_server_thread = None
is_server_running = False
server_task = None
connected_clients = set()
loop = None

# Store last few messages for logging
message_history = []
MAX_MESSAGE_HISTORY = 10

# Function to handle incoming websocket messages
async def handle_message(websocket, path):
    """Handle incoming websocket connection and messages"""
    # Add the client to our set
    client_info = websocket.remote_address
    client_ip = client_info[0] if client_info else "Unknown"
    connected_clients.add(websocket)
    
    # Set the ESP connection status in the UI
    def update_connection_status():
        bpy.context.scene.server_settings.esp_connected = True
        bpy.context.scene.server_settings.esp_ip = client_ip
        bpy.context.scene.debug_settings.connection_status = f"Connected to {client_ip}"
        return None  # Don't repeat the timer
        
    timers.register(update_connection_status)
    
    print(f"WebSocket Test: Client connected from {client_ip}")
    
    try:
        # Process messages from this client
        async for message in websocket:
            # Store message in history
            message_history.insert(0, message)
            if len(message_history) > MAX_MESSAGE_HISTORY:
                message_history.pop()
            
            # Update the UI with received message
            def update_debug_info():
                bpy.context.scene.debug_settings.last_message = message[:500]  # Truncate if too long
                
                # Update message log (last 5 messages)
                log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(message_history[:5])])
                bpy.context.scene.debug_settings.message_log = log
                
                return None  # Don't repeat timer
                
            timers.register(update_debug_info)
            
            # Print the message to console
            print(f"WebSocket Test: Received message: {message}")
            
            try:
                # Try to parse as JSON
                data = json.loads(message)
                print(f"WebSocket Test: Parsed JSON: {data}")
                
            except json.JSONDecodeError:
                print(f"WebSocket Test: Message is not valid JSON")
            except Exception as e:
                print(f"WebSocket Test: Error processing message: {str(e)}")
    
    finally:
        # Remove the client from our set when they disconnect
        connected_clients.remove(websocket)
        
        # Update the UI to show disconnection
        def update_disconnection_status():
            if len(connected_clients) == 0:
                bpy.context.scene.server_settings.esp_connected = False
                bpy.context.scene.server_settings.esp_ip = ""
                bpy.context.scene.debug_settings.connection_status = "Disconnected"
            return None  # Don't repeat the timer
            
        timers.register(update_disconnection_status)
        print(f"WebSocket Test: Client {client_ip} disconnected")

# Function to start the websocket server
async def start_server_async(host, port):
    """Start the websocket server asynchronously"""
    global server_task
    
    server = await websockets.serve(handle_message, host, port)
    server_task = server
    print(f"WebSocket Test: Server started at {host}:{port}")
    
    # Keep the server running
    await asyncio.Future()  # Run forever

# Server thread function
def run_websocket_server(host, port):
    """Run the websocket server in a separate thread"""
    global loop
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start the server
    try:
        loop.run_until_complete(start_server_async(host, port))
        loop.run_forever()
    except Exception as e:
        print(f"WebSocket Test: Error in server thread: {str(e)}")

# Function to start the server
def start_server(host, port):
    """Start the websocket server"""
    global websocket_server_thread, is_server_running
    
    if is_server_running:
        print("WebSocket Test: Server already running")
        return False
    
    try:
        # Create and start the server thread
        websocket_server_thread = threading.Thread(
            target=run_websocket_server, 
            args=(host, port)
        )
        websocket_server_thread.daemon = True
        websocket_server_thread.start()
        
        is_server_running = True
        return True
        
    except Exception as e:
        print(f"WebSocket Test: Error starting server: {str(e)}")
        return False

# Function to stop the server
def stop_server():
    """Stop the websocket server"""
    global is_server_running, loop, server_task
    
    if not is_server_running:
        print("WebSocket Test: Server not running")
        return False
    
    try:
        # Cancel all active websocket connections and server task
        if loop and loop.is_running():
            async def cleanup():
                # Close all client connections
                for websocket in connected_clients.copy():
                    await websocket.close()
                
                # Close the server
                if server_task:
                    server_task.ws_server.close()
                    await server_task.ws_server.wait_closed()
            
            # Schedule the cleanup coroutine in the event loop
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(cleanup(), loop)
                try:
                    future.result(timeout=5)  # Wait up to 5 seconds for cleanup
                except Exception as e:
                    print(f"WebSocket Test: Error during server cleanup: {str(e)}")
                
                # Stop the event loop
                loop.call_soon_threadsafe(loop.stop)
        
        # Reset global variables
        connected_clients.clear()
        is_server_running = False
        
        # Update UI to show disconnection
        bpy.context.scene.server_settings.esp_connected = False
        bpy.context.scene.server_settings.esp_ip = ""
        bpy.context.scene.debug_settings.connection_status = "Server stopped"
        
        print("WebSocket Test: Server stopped")
        return True
        
    except Exception as e:
        print(f"WebSocket Test: Error stopping server: {str(e)}")
        return False

# Function to send a test message to all connected clients
def send_test_message():
    """Send a test message to all connected clients"""
    if not is_server_running or not connected_clients:
        print("WebSocket Test: No clients connected")
        return False
    
    try:
        # Create a test message
        test_message = {
            "type": "test_message",
            "message": "Hello from Blender!"
        }
        
        # Convert to JSON
        json_message = json.dumps(test_message)
        
        # Send to all clients
        for client in connected_clients:
            asyncio.run_coroutine_threadsafe(
                client.send(json_message),
                loop
            )
        
        print(f"WebSocket Test: Sent test message to {len(connected_clients)} client(s)")
        return True
        
    except Exception as e:
        print(f"WebSocket Test: Error sending test message: {str(e)}")
        return False

def register():
    """No special registration needed for this module"""
    pass

def unregister():
    """Stop server if running when addon is disabled"""
    if is_server_running:
        stop_server()