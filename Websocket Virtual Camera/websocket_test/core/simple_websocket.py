# Create a new file: simple_websocket.py
import socket
import threading
import select
import base64
import hashlib
import struct
import json
import time
import bpy
from bpy.app import timers

# Global variables
websocket_server_thread = None
is_server_running = False
server_socket = None
connected_clients = set()
client_handshake_complete = {}
message_history = []
MAX_MESSAGE_HISTORY = 10

# WebSocket handshake magic string
MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def process_imu_data(data):
    """Process IMU data and update the camera if enabled"""
    scene = bpy.context.scene
    camera_settings = scene.camera_tracking
    
    # Check if message contains a cam_id
    cam_id = data.get("cam_id", "")
    
    # Get the cameras to update (based on cam_id)
    target_cameras = []
    
    if cam_id:
        # Find the specific camera with the matching ID
        for cam in camera_settings.cameras:
            if cam.cam_id == cam_id:
                # Found matching camera
                if cam.camera_name in bpy.data.objects:
                    camera_obj = bpy.data.objects[cam.camera_name]
                    target_cameras.append(camera_obj)
                    break
    else:
        # No cam_id specified, update all cameras
        for cam in camera_settings.cameras:
            if cam.camera_name in bpy.data.objects:
                camera_obj = bpy.data.objects[cam.camera_name]
                target_cameras.append(camera_obj)
    
    # Fall back to legacy field if no cameras found
    if not target_cameras and camera_settings.target_camera:
        try:
            camera = bpy.data.objects[camera_settings.target_camera]
            target_cameras.append(camera)
        except KeyError:
            print(f"WebSocket Test: Camera '{camera_settings.target_camera}' not found")
            return
    
    # If still no cameras, exit
    if not target_cameras:
        print("WebSocket Test: No target cameras found")
        return
    
    # Process each camera
    for camera in target_cameras:
        # Update rotation if enabled
        if camera_settings.track_rotation and "rot_x" in data and "rot_y" in data and "rot_z" in data:
            try:
                factor = camera_settings.rotation_factor
                
                # Convert degrees to radians (multiply by pi/180)
                deg_to_rad = 3.14159265359 / 180.0
                
                # Get rotation offsets in radians
                offset_x = camera_settings.rotation_offset_x  # Already in radians because of subtype='ANGLE'
                offset_y = camera_settings.rotation_offset_y  # Already in radians because of subtype='ANGLE'
                offset_z = camera_settings.rotation_offset_z  # Already in radians because of subtype='ANGLE'
                
                # Apply rotations from IMU plus offsets
                camera.rotation_euler.x = float(data["rot_x"]) * factor * deg_to_rad + offset_x
                camera.rotation_euler.y = float(data["rot_y"]) * factor * deg_to_rad + offset_y
                camera.rotation_euler.z = float(data["rot_z"]) * factor * deg_to_rad + offset_z
                
                print(f"WebSocket Test: Updated camera '{camera.name}' rotation: {camera.rotation_euler}")
            except Exception as e:
                print(f"WebSocket Test: Error updating camera rotation: {str(e)}")
        
        # Update location if enabled
        if camera_settings.track_location and "loc_x" in data and "loc_y" in data and "loc_z" in data:
            try:
                factor = camera_settings.location_factor
                
                # Always use local location since we have a parent
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
                
                print(f"WebSocket Test: Updated camera '{camera.name}' location: {camera.location}")
            except Exception as e:
                print(f"WebSocket Test: Error updating camera location: {str(e)}")
        
        # Update location if enabled
        if camera_settings.track_location and "loc_x" in data and "loc_y" in data and "loc_z" in data:
            try:
                factor = camera_settings.location_factor
                
                if is_hybrid:
                    # In hybrid setup, we set local location relative to parent
                    camera.location.x = float(data["loc_x"]) * factor
                    camera.location.y = float(data["loc_y"]) * factor
                    camera.location.z = float(data["loc_z"]) * factor
                else:
                    # Regular setup, set world location
                    camera.location.x = float(data["loc_x"]) * factor
                    camera.location.y = float(data["loc_y"]) * factor
                    camera.location.z = float(data["loc_z"]) * factor
                
                print(f"WebSocket Test: Updated camera '{camera.name}' location: {camera.location}")
            except Exception as e:
                print(f"WebSocket Test: Error updating camera location: {str(e)}")
    
    # Update location if enabled
    if camera_settings.track_location and "loc_x" in data and "loc_y" in data and "loc_z" in data:
        try:
            factor = camera_settings.location_factor
            
            if is_hybrid:
                # In hybrid setup, we set local location relative to parent
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            else:
                # Regular setup, set world location
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            
            print(f"WebSocket Test: Updated camera location: {camera.location}")
        except Exception as e:
            print(f"WebSocket Test: Error updating camera location: {str(e)}")
    
    # Update location if enabled
    if camera_settings.track_location and "loc_x" in data and "loc_y" in data and "loc_z" in data:
        try:
            factor = camera_settings.location_factor
            
            if is_hybrid:
                # In hybrid setup, we set local location relative to parent
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            else:
                # Regular setup, set world location
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            
            print(f"WebSocket Test: Updated camera location: {camera.location}")
        except Exception as e:
            print(f"WebSocket Test: Error updating camera location: {str(e)}")
    
    # Update location if enabled
    if camera_settings.track_location and "loc_x" in data and "loc_y" in data and "loc_z" in data:
        try:
            factor = camera_settings.location_factor
            
            if is_hybrid:
                # In hybrid setup, we set local location relative to parent
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            else:
                # Regular setup, set world location
                camera.location.x = float(data["loc_x"]) * factor
                camera.location.y = float(data["loc_y"]) * factor
                camera.location.z = float(data["loc_z"]) * factor
            
            print(f"WebSocket Test: Updated camera location: {camera.location}")
        except Exception as e:
            print(f"WebSocket Test: Error updating camera location: {str(e)}")

def handshake(client_socket, data):
    """Complete the WebSocket handshake with the client"""
    # Convert to string for easier parsing
    request = data.decode('utf-8', errors='ignore')
    
    # Parse the Sec-WebSocket-Key header
    key = None
    for line in request.split('\r\n'):
        if line.startswith('Sec-WebSocket-Key:'):
            key = line.split(':', 1)[1].strip()
            break
    
    if not key:
        print("WebSocket Test: No Sec-WebSocket-Key found")
        return False
    
    print(f"WebSocket Test: Found key: {key}")
    
    # Create the accept key
    accept_key = base64.b64encode(
        hashlib.sha1((key + MAGIC_STRING).encode('utf-8')).digest()
    ).decode('utf-8')
    
    # Create the handshake response
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key}\r\n"
        "\r\n"
    )
    
    # Send the response
    client_socket.send(response.encode('utf-8'))
    print(f"WebSocket Test: Handshake completed with {client_socket.getpeername()}")
    return True

def decode_frame(data):
    """Decode a WebSocket frame"""
    if len(data) < 6:
        return None
    
    # First byte: FIN bit and opcode
    fin = (data[0] & 0x80) != 0
    opcode = data[0] & 0x0F
    
    # Second byte: MASK bit and payload length
    masked = (data[1] & 0x80) != 0
    payload_len = data[1] & 0x7F
    
    # Handle different payload length formats
    if payload_len == 126:
        mask_start = 4
        payload_len = struct.unpack(">H", data[2:4])[0]
    elif payload_len == 127:
        mask_start = 10
        payload_len = struct.unpack(">Q", data[2:10])[0]
    else:
        mask_start = 2
    
    # Get masking key and payload
    if not masked:
        return None
    
    mask_key = data[mask_start:mask_start+4]
    payload_start = mask_start + 4
    
    # Check if we have enough data
    if payload_start + payload_len > len(data):
        return None
    
    # Unmask the payload
    payload = bytearray(payload_len)
    for i in range(payload_len):
        if payload_start + i < len(data):
            payload[i] = data[payload_start + i] ^ mask_key[i % 4]
    
    # Handle different opcodes
    if opcode == 0x1:  # Text
        try:
            return payload.decode('utf-8')
        except:
            return None
    elif opcode == 0x8:  # Close
        return None
    else:
        return None

def encode_frame(message):
    """Encode a message as a WebSocket frame"""
    if isinstance(message, str):
        message = message.encode('utf-8')
    
    # Create header
    header = bytearray()
    
    # First byte: FIN bit and opcode for text
    header.append(0x81)  # 1000 0001 - FIN bit set and text opcode
    
    # Second byte: payload length (no mask)
    length = len(message)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(127)
        header.extend(struct.pack(">Q", length))
    
    # Return the complete frame
    return header + message

def handle_message(client_socket, message):
    """Process a received message"""
    try:
        # Add to message history
        message_history.insert(0, message)
        if len(message_history) > MAX_MESSAGE_HISTORY:
            message_history.pop()
        
        # Update UI
        def update_ui():
            bpy.context.scene.debug_settings.last_message = message[:500]
            log = "\n".join([f"[{i+1}] {msg[:100]}..." for i, msg in enumerate(message_history[:5])])
            bpy.context.scene.debug_settings.message_log = log
            return None
        
        timers.register(update_ui)
        
        # Parse JSON
        data = json.loads(message)
        print(f"WebSocket Test: Received JSON: {data}")
        
        # Check for IMU data
        if data.get("type") == "IMU":
            # Process IMU data
            def update_camera():
                process_imu_data(data)
                return None
            
            timers.register(update_camera)
    
    except json.JSONDecodeError:
        print(f"WebSocket Test: Invalid JSON: {message}")
    except Exception as e:
        print(f"WebSocket Test: Error processing message: {str(e)}")

def server_loop(host, port):
    """Main server loop"""
    global server_socket, is_server_running, connected_clients, client_handshake_complete
    
    try:
        # Create socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind and listen
        server_socket.bind((host, port))
        server_socket.listen(5)
        
        print(f"WebSocket Test: Server running on {host}:{port}")
        
        # Set up client buffers
        client_buffers = {}
        
        while is_server_running:
            # Select with timeout
            readable, _, exceptional = select.select(
                [server_socket] + list(connected_clients),
                [],
                list(connected_clients),
                1.0
            )
            
            for sock in readable:
                # Accept new connection
                if sock == server_socket:
                    client, address = server_socket.accept()
                    print(f"WebSocket Test: New connection from {address[0]}:{address[1]}")
                    
                    # Set up for this client
                    connected_clients.add(client)
                    client_handshake_complete[client] = False
                    client_buffers[client] = b""
                    
                    # Non-blocking mode
                    client.setblocking(0)
                
                # Handle client data
                else:
                    try:
                        # Receive data
                        data = sock.recv(4096)
                        
                        if not data:
                            raise ConnectionError("Client closed connection")
                        
                        # Check if handshake is complete
                        if not client_handshake_complete.get(sock, False):
                            # Add to buffer
                            client_buffers[sock] += data
                            
                            # Check for HTTP request
                            if b"GET" in client_buffers[sock] and b"Upgrade: websocket" in client_buffers[sock]:
                                # Try to complete handshake
                                if handshake(sock, client_buffers[sock]):
                                    client_handshake_complete[sock] = True
                                    client_buffers[sock] = b""
                                    
                                    # Update UI
                                    def update_connection():
                                        bpy.context.scene.server_settings.esp_connected = True
                                        bpy.context.scene.server_settings.esp_ip = sock.getpeername()[0]
                                        bpy.context.scene.debug_settings.connection_status = f"Connected to {sock.getpeername()[0]}"
                                        return None
                                    
                                    timers.register(update_connection)
                        
                        # Process WebSocket frames
                        else:
                            message = decode_frame(data)
                            if message:
                                handle_message(sock, message)
                    
                    except ConnectionError as e:
                        print(f"WebSocket Test: Client disconnected: {e}")
                        
                        # Clean up
                        connected_clients.remove(sock)
                        if sock in client_handshake_complete:
                            del client_handshake_complete[sock]
                        if sock in client_buffers:
                            del client_buffers[sock]
                        
                        sock.close()
                        
                        # Update UI if no clients left
                        if not connected_clients:
                            def update_disconnect():
                                bpy.context.scene.server_settings.esp_connected = False
                                bpy.context.scene.server_settings.esp_ip = ""
                                bpy.context.scene.debug_settings.connection_status = "Disconnected"
                                return None
                            
                            timers.register(update_disconnect)
            
            # Handle exceptions
            for sock in exceptional:
                print(f"WebSocket Test: Exception on client socket")
                
                # Clean up
                if sock in connected_clients:
                    connected_clients.remove(sock)
                if sock in client_handshake_complete:
                    del client_handshake_complete[sock]
                if sock in client_buffers:
                    del client_buffers[sock]
                
                sock.close()
    
    except Exception as e:
        print(f"WebSocket Test: Server error: {str(e)}")
    
    finally:
        if server_socket:
            server_socket.close()

def start_server(host, port):
    """Start the WebSocket server"""
    global websocket_server_thread, is_server_running
    
    if is_server_running:
        return False
    
    # Start server
    is_server_running = True
    bpy.types.Scene.server_running = True  # Set the global flag
    
    websocket_server_thread = threading.Thread(target=server_loop, args=(host, port))
    websocket_server_thread.daemon = True
    websocket_server_thread.start()
    
    return True

def stop_server():
    """Stop the WebSocket server"""
    global is_server_running
    
    if not is_server_running:
        return False
    
    # Stop server
    is_server_running = False
    bpy.types.Scene.server_running = False  # Clear the global flag
    
    # Close all clients
    for client in connected_clients.copy():
        try:
            client.close()
        except:
            pass
    
    connected_clients.clear()
    
    # Wait for thread to end
    if websocket_server_thread:
        websocket_server_thread.join(timeout=2.0)
    
    # Update UI
    bpy.context.scene.server_settings.esp_connected = False
    bpy.context.scene.server_settings.esp_ip = ""
    bpy.context.scene.debug_settings.connection_status = "Server stopped"
    
    return True

def send_test_message():
    """Send a test message to all connected clients"""
    if not is_server_running or not connected_clients:
        return False
    
    # Create message
    message = {
        "type": "test",
        "message": "Hello from Blender!",
        "timestamp": int(time.time() * 1000)
    }
    
    # Convert to JSON
    json_str = json.dumps(message)
    
    # Send to all clients
    for client in connected_clients.copy():
        try:
            if client in client_handshake_complete and client_handshake_complete[client]:
                frame = encode_frame(json_str)
                client.send(frame)
        except:
            pass
    
    return True

def register():
    pass

def unregister():
    if is_server_running:
        stop_server()