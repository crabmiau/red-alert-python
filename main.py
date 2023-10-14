import requests
import time
from datetime import datetime
import json

# Define the API endpoint
api_url = "https://api.tzevaadom.co.il/notifications"

# Function to fetch alerts from the API
def get_alerts():
    try:
        response = requests.get(api_url)
        data = response.json()
        return data
    except Exception as e:
        print("Error fetching data:", e)
        return []
    
def send_dc(webhook_url, message):
    payload = {
        "content": message
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord webhook: {e}")

def format_time(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('%H:%M:%S')
# Function to compare and print new alerts
def check_for_new_alerts(previous_alerts):
    current_alerts = get_alerts()

    if current_alerts != previous_alerts:
        new_alerts = [alert for alert in current_alerts if alert not in previous_alerts]
        if new_alerts:
            for alert in new_alerts:
                threatlevel = "Unknown"  # Set a default value for 'threatlevel'  if none match
                threat = "Unknown"  # Set a default value for 'threat' if none match
                if alert['isDrill']:
                    threatlevel = "No"
                else:
                    threatlevel = "Yes"
                if alert['threat'] == 0:
                    threat = "Missiles"
                elif alert['threat'] == 2:
                    threat = "Terrorist infiltration"
                elif alert['threat'] == 5:
                    threat = "Hostile aircraft intrusion"
                else:
                    threat = alert['threat']
                builder = f"||@everyone||\n{format_time(alert['time'])}\n\nThreat: {threat}\nReal threat?: {threatlevel}\nAffected cities: {', '.join(alert['cities'])}\n**If you are in any of these cities, Enter a protected space and stay there for 10 minutes**"
                send_dc("Your Discord Webhook here",builder)
        return current_alerts
    return previous_alerts

if __name__ == "__main__":
    previous_alerts = []

    while True:
        previous_alerts = check_for_new_alerts(previous_alerts)
        time.sleep(2)  # Check for new alerts every 2 seconds
