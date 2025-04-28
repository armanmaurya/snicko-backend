import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get user_id from the URL parameter (passed in WebSocket URL)
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f"user_{self.user_id}"

        print(f"[DEBUG] Connecting WebSocket for user_id: {self.user_id}, group_name: {self.group_name}")

        # Join the user-specific group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        print(f"[DEBUG] Added to group: {self.group_name}")

        # Accept the WebSocket connection
        await self.accept()
        print(f"[DEBUG] WebSocket connection accepted for user_id: {self.user_id}")

        # Send a "connected" message to the WebSocket client
        connected_message = {
            "title": "connection_status",
            "body": "WebSocket connection established successfully."
        }
        await self.send(text_data=json.dumps(connected_message))
        print(f"[DEBUG] Sent connected message to WebSocket: {connected_message}")

    async def disconnect(self, close_code):
        print(f"[DEBUG] Disconnecting WebSocket for user_id: {self.user_id}, close_code: {close_code}")

        # Leave the user-specific group when the WebSocket disconnects
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"[DEBUG] Removed from group: {self.group_name}")

    # Receive message from WebSocket
    async def receive(self, text_data):
        print(f"[DEBUG] Received message from WebSocket: {text_data}")

        # Echo back received data for now
        await self.send(text_data=text_data)
        print(f"[DEBUG] Sent message back to WebSocket: {text_data}")

    # Method to send notification to WebSocket
    async def send_notification(self, event):
        print(f"[DEBUG] Sending notification to WebSocket: {event['content']}")

        # Send notification data to WebSocket
        await self.send(text_data=json.dumps(event["content"]))
        print(f"[DEBUG] Notification sent to WebSocket: {event['content']}")
