## Steps for installing on RPI
1. git clone https://github.com/Canopyflick/Manon-PA_bot.git
2. cd Manon-PA_bot
3. python3 -m venv venv
4. source venv/bin/activate
5. pip3 install -r requirements.txt
6. nano .env
7. Enter all required secrets (see template below)
8. Create database on rpi if you haven't yet:
    - Log into PostgreSQL:
      ```bash
      psql -U postgres
      ```
    - List all databases:
      ```sql
      \l
      ```
    - Create the database:
      ```sql
      CREATE DATABASE mydbname
        WITH
        OWNER = postgres
        ENCODING = 'UTF8'
        LC_COLLATE = 'en_GB.UTF-8'
        LC_CTYPE = 'en_GB.UTF-8'
        CONNECTION LIMIT = -1;
      ```
    - Exit `psql`:
      ```sql
      \q
      ```
    - Confirm the database URL in your `.env` points to this database:
      ```plaintext
      DATABASE_URL=postgresql://postgres:<password>@localhost/mydbname
      ```
9. python main.py
10. 🥳

## .env File (also see env.template)
TELEGRAM_API_KEY=
OPENAI_API_KEY=
DATABASE_URL=postgresql://postgres:<password>@<ip>/mydbname?timezone=Europe/Berlin | postgresql://postgres:<password>@localhost/mydbname?timezone=Europe/Berlin
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="<key>"
LANGCHAIN_PROJECT="PA_bot_test"
