from utils.helpers import get_database_connection, get_first_name, datetime, timedelta, BERLIN_TZ
import logging



# Function to get existing columns
def get_existing_columns(cursor, conn, table_name):
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public';
    """, (table_name,))
    conn.commit()
    return [info[0] for info in cursor.fetchall()]


# Function to add missing columns
def add_missing_columns(cursor, conn, table_name, desired_columns):
    existing_columns = get_existing_columns(cursor, conn, table_name)
    for column_name, column_definition in desired_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};")
                logging.info(f"Added column {column_name} to {table_name}")
            except Exception as e:
                logging.error(f"Error adding column {column_name}: {e}")
                conn.rollback()  # Roll back the specific column addition if it fails




def setup_database():
    conn = get_database_connection()
    cursor = conn.cursor()
    try:

        # Desired columns with definitions
        desired_columns_manon_users = {
            'user_id': 'BIGINT',
            'chat_id': 'BIGINT',
        }

        # Create the tables if they don't exist
        #1 manon_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manon_users (
                user_id BIGINT,
                chat_id BIGINT,
                first_name TEXT DEFAULT "Josefientje",
                score FLOAT DEFAULT 0,
                inventory JSONB DEFAULT '{"boosts": 1, "challenges": 1, "links": 1}',
                any_reminder_scheduled BOOLEAN DEFAULT False,
                long_term_goals TEXT DEFAULT NULL,       
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        conn.commit()
    
        #2 manon_goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manon_goals (
                goal_id SERIAL PRIMARY KEY,
                group_id BIGINT DEFAULT NULL,           -- Group ID for recurring goals       
                user_id BIGINT NOT NULL,                -- Foreign key to identify the user
                chat_id BIGINT NOT NULL,                -- Foreign key to identify the chat 
                status TEXT DEFAULT 'pending' CHECK (status IN (
                    'prepared', 'pending', 'paused', 'archived_done', 'archived_failed', 'archived_canceled'
                )),
		        goal_durability TEXT NOT NULL DEFAULT 'one-time' CHECK (goal_durability IN ('one-time', 'recurring')),
                goal_timeframe TEXT NOT NULL CHECK (goal_timeframe IN ('today', 'by_date', 'open-ended')),       
                goal_value FLOAT NOT NULL,   

                description TEXT NOT NULL,
                set_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,       -- Time when the goal was set
                deadline TIMESTAMP CHECK (
                    (goal_timeframe = 'open-ended' AND deadline IS NULL) OR
                    (goal_timeframe IN ('today', 'by_date') AND deadline IS NOT NULL)
                ),

                reminder_time TIMESTAMP DEFAULT NULL,       
                reminder_scheduled BOOLEAN DEFAULT False,
                time_investment_value FLOAT NOT NULL,    
		        difficulty_multiplier FLOAT NOT NULL,
		        impact_multiplier FLOAT NOT NULL,
                penalty FLOAT DEFAULT 0 NOT NULL,       
                iteration INTEGER DEFAULT 1,            -- N+1, either for tracking attempts at one-time goals (retries), or index of recurring
                final_iteration TEXT DEFAULT 'not_applicable' CHECK (final_iteration IN ('not_applicable', 'false', 'true')),  -- The last iteration of a recurring goal. Should only be None for one-time goals, and can be used to prompt evaluation of extension       
                goal_category TEXT[] NOT NULL,            -- eg work, productivity, chores, relationships, hobbies, self-development, wealth, impact (EA), health, fun, other       
                completed_time TIMESTAMP DEFAULT NULL,                           -- Time when the goal was completed
                FOREIGN KEY (user_id, chat_id) REFERENCES manon_users (user_id, chat_id)
            )
        ''')
        conn.commit()
    
        #3 manon_bot table
        # Set 4 AM as default last_reset_time
        now = datetime.now(tz=BERLIN_TZ)
        unformatted_time = now.replace(hour=4, minute=0, second=0, microsecond=0) - timedelta(days=1)
        four_am_last_night = unformatted_time.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS manon_bot (
            last_reset_time TIMESTAMP DEFAULT %s
            )
        ''', (four_am_last_night,))
        conn.commit()

        # Add missing columns
        add_missing_columns(cursor, conn, 'manon_users', desired_columns_manon_users)
        conn.commit()

        #4 goal history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS goal_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT,
            chat_id BIGINT,
            goal_text TEXT NOT NULL,
            completion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            goal_type TEXT NOT NULL DEFAULT 'personal', -- 'personal' or 'challenges'
            challenge_from BIGINT,  -- NULL for personal goals, user_id of challenger for challenges
            FOREIGN KEY (user_id, chat_id) REFERENCES users(user_id, chat_id) ON DELETE CASCADE,
            FOREIGN KEY (challenge_from, chat_id) REFERENCES users(user_id, chat_id) ON DELETE CASCADE
        );
        ''')
        conn.commit()
    
        #5 polls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
            chat_id BIGINT NOT NULL,
            poll_id VARCHAR(255) NOT NULL,
            message_id BIGINT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (poll_id)
        );
        ''')
        conn.commit()
        
    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()



    

async def collect_meta_data(user_id, chat_id):
    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        # 1. Query to fetch user stats from the users table
        cursor.execute('''
            SELECT total_goals, completed_goals, score, today_goal_status, today_goal_text, inventory
            FROM manon_users
            WHERE user_id = %s AND chat_id = %s;
        ''', (user_id, chat_id))
        user_data = cursor.fetchone()
        
        if user_data:
            total_goals, completed_goals, score, today_goal_status, today_goal_text, inventory = user_data
        else:
            return "No user data found."

        # 2. Query to get live engagements (like challenges, links, boosts) for the user
        cursor.execute('''
            SELECT engager_id, special_type, status
            FROM engagements
            WHERE engaged_id = %s AND chat_id = %s AND status IN ('live', 'pending');
        ''', (user_id, chat_id))
        live_engagements = cursor.fetchall()

        # 3. Query to get the last reset time from the bot_status table
        cursor.execute('''
            SELECT last_reset_time
            FROM bot_status;
        ''')
        last_reset_time = cursor.fetchone()[0]

        # 4. Query to get goal history for the user
        cursor.execute('''
            SELECT goal_text, completion_time, goal_type, challenge_from
            FROM goal_history
            WHERE user_id = %s AND chat_id = %s
            ORDER BY completion_time DESC
            LIMIT 5;
        ''', (user_id, chat_id))
        recent_goals = cursor.fetchall()

        # 5. Query to rank all users by score in this chat
        cursor.execute('''
            SELECT user_id, score
            FROM users
            WHERE chat_id = %s
            ORDER BY score DESC;
        ''', (chat_id,))
        score_ranking = cursor.fetchall()

        # Find the current user's rank
        user_rank = None
        for rank, (uid, score) in enumerate(score_ranking, start=1):
            if uid == user_id:
                user_rank = rank
                break

        # Construct a meta-data dictionary
        meta_data = {
            "total_goals": total_goals,
            "completed_goals": completed_goals,
            "score": score,
            "today_goal_status": today_goal_status,
            "today_goal_text": today_goal_text,
            "inventory": inventory,
            "live_engagements": live_engagements,
            "last_reset_time": last_reset_time,
            "recent_goals": recent_goals,
            "score_ranking": score_ranking,
            "user_rank": user_rank
        }
        logging.info(f"\n\n⏺️⏺️⏺️Dit is de metadata in de collect-functie: {meta_data}\n")
        return meta_data

    except Exception as e:
        logging.error(f"Error collecting meta data: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# Dummy function, not yet interacting with db        
async def fetch_long_term_goals(chat_id, user_id):
    return "To be increasingly kind and useful to others. To set myself up for continuous learning, self-improvement, longevity and rich relationships."