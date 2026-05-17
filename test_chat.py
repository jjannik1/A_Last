import asyncio
import aiohttp
import json

async def test_chat():
    async with aiohttp.ClientSession() as session:
        # First login to get a session cookie
        login_data = {"username": "admin", "password": "123"}
        try:
            async with session.post('http://127.0.0.1:8000/login', data=login_data) as resp:
                print("Login status:", resp.status)
                if resp.status != 200:
                    print("Failed to login, skipping chat test")
                    return
        except Exception as e:
            print("Cannot connect to server:", e)
            return

        print("Testing websocket connection...")
        try:
            async with session.ws_connect('ws://127.0.0.1:8000/ws/chat/testuser123') as ws:
                print("Connected to websocket")
                await ws.send_json({
                    "receiver_id": "testuser456",
                    "content": "Hello world"
                })
                print("Sent message")
                
                # Receive message
                msg = await ws.receive()
                print("Received:", msg.data)
        except Exception as e:
            print("Websocket error:", e)

if __name__ == "__main__":
    asyncio.run(test_chat())
