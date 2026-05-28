from datetime import datetime

LITURGICAL_CALENDAR = {
    "01-01": "📜 Solemnity of Mary: 'The Lord bless you and keep you.' - Numbers 6:24",
    "12-25": "📜 Christmas: 'For to us a child is born, to us a son is given.' - Isaiah 9:6",
    "05-26": "📜 Daily Mass: 'Your word is a lamp to my feet and a light to my path.' - Psalm 119:105",
}

def get_today_reading():
    today_key = datetime.now().strftime("%m-%d")
    fallback = "📜 Daily Devotional: 'Trust in the Lord with all your heart.' - Proverbs 3:5"
    return LITURGICAL_CALENDAR.get(today_key, fallback)