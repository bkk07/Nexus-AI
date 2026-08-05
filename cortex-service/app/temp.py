from dotenv import load_dotenv
from app.tools.gmail.tools import gmail_search_emails

load_dotenv()
res = gmail_search_emails.invoke({"max_results": 2})
print(res)