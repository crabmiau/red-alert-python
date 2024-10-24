import json
import requests
import time
import websockets
import asyncio

webhook = ""

def load_cities_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

api_url = "ws://ws.cumta.morhaviv.com:25565/ws"  # WebSocket URL for alerts

cities_data = load_cities_from_file('city.json')

ongoing_notifications = {}  # Stores notifications by cumta_id

def send_webhook(message_parts):
    for message in message_parts:
        payload = {
            "content": message
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{webhook}?wait=true", data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print("Alert sent to Discord.")
            return response.json()['id']
        except requests.exceptions.RequestException as e:
            print(f"Error (at send): {e}")
            return None

def edit_webhook(message_id, new_message_parts):
    for i, message in enumerate(new_message_parts):
        url = f"{webhook}/messages/{message_id}"
        payload = {
            "content": message
        }
        headers = {
            "Content-Type": "application/json"
        }
        try:
            response = requests.patch(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print(f"Alert edited: {message_id}, part {i+1}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error (at edit): {e}")
            return None

def get_city_info(city_name):
    city_info = cities_data['cities'].get(city_name)
    if city_info:
        return city_info['en'], city_info['countdown']
    else:
        return None, None
    
threat_levels = {
    1: "Missiles"
}

def split_message(message, limit=2000):
    messages = []
    while len(message) > limit:
        split_point = message.rfind('\n', 0, limit)
        if split_point == -1:
            split_point = limit
        messages.append(message[:split_point])
        message = message[split_point:].strip()
    messages.append(message)
    return messages

def create_message(notification):
    latest_time = notification['time']
    threat = threat_levels.get(notification['threat'], "Unknown Threat")

    sorted_cities = sorted(notification['cities'])
    affected_cities = []

    for city in sorted_cities:
        city_en, countdown = get_city_info(city)
        if city_en and countdown is not None:
            affected_cities.append(f"- {city_en}: **{countdown} seconds**")

    builder = (
        f"||<@&1288096042419490927>||\n"
        f"<t:{latest_time}:f> (<t:{latest_time}:R>) (timestamp: {latest_time})\n\n"
        f"**:rotating_light: Alert:**\n"
        f"**Threat:** **{threat}**\n\n"
        f"**Affected Cities:**\n"
        + "\n".join(affected_cities) + "\n"
    )
    
    return split_message(builder)

async def alert_handler():
    while True:  # Keep trying to connect indefinitely
        try:
            async with websockets.connect(api_url) as websocket:
                while True:
                    try:
                        received_message = await websocket.recv()
                        alert = json.loads(received_message)

                        cumta_id = alert['cumta_id']
                        print(alert['type'])
                        alert_time = int(time.time())

                        if cumta_id in ongoing_notifications:
                            print(f"Updating existing alert for cumta_id: {cumta_id} ({alert['type']})")
                            notification = ongoing_notifications[cumta_id]
                            notification['time'] = alert_time
                            notification['cities'].update(alert['areas'].split(", "))
                            edit_webhook(notification['message_id'], create_message(notification))
                        else:
                            print(f"New alert for cumta_id: {cumta_id} ({alert['type']})")
                            ongoing_notifications[cumta_id] = {
                                'time': alert_time,
                                'threat': alert['type'],
                                'cities': set(alert['areas'].split(", ")),
                                'message_id': None
                            }
                            notification = ongoing_notifications[cumta_id]
                            notification['message_id'] = send_webhook(create_message(notification))

                    except json.JSONDecodeError:
                        print("Received invalid JSON.")
                    except websockets.exceptions.ConnectionClosedError as e:
                        print(f"WebSocket connection error: {e}")
                        break  # Exit the inner loop, attempt to reconnect
                    except Exception as e:
                        print(f"Error processing alert: {e}")
                        await asyncio.sleep(5)
        except TimeoutError:
            print("WebSocket connection timed out. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error establishing WebSocket connection: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)


async def main():
    while True:
        try:
            await alert_handler()
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket closed unexpectedly: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
