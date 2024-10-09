import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async  # Import this for async ORM calls

from .models import Notification


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'chat_{self.user_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Get the count of all unread notifications for the user
        unread_count = await self.get_unread_notification_count(self.user_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_notification_count',
                'count': unread_count
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def send_notification(self, event):
        message = event['message']
        print("Notification received:", message)
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def send_notification_count(self, event):
        count = event['count']
        print("Notification count received:", count)
        # Send notification count to WebSocket
        await self.send(text_data=json.dumps({
            'noti_count': count
        }))

    @database_sync_to_async
    def get_unread_notification_count(self, user_id):
        return Notification.objects.filter(user__id=user_id, is_read=False).count()
