from utils.helpers import get_database_connection, get_first_name, datetime, timedelta, BERLIN_TZ, PA
import logging




async def update_goal_data(goal_id, **kwargs):
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
    
        updates = ', '.join(f"{key} = %s" for key in kwargs.keys())
        values = list(kwargs.values())
        values.append(goal_id)

        cursor.execute(f'''
            UPDATE manon_goals
            SET {updates}
            WHERE goal_id = %s;
        ''', values)
        conn.commit()
    except Exception as e:
        logging.error(f'Error updating goal data in update_goal_data(): \n{e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        
        
async def create_limbo_goal(update, context):
    chat_id=update.effective_chat.id
    user_id = update.effective_user.id
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
   
        cursor.execute('''
            INSERT INTO manon_goals (
                user_id,
                chat_id,
                status
            ) VALUES (%s, %s, %s)
            RETURNING goal_id;
        ''', (user_id, chat_id, 'limbo'))
        conn.commit()
        brand_new_goal_id = cursor.fetchone()[0]
        logging.info(f"\nNew Limbo Goal Created: {brand_new_goal_id}\n")
        
        return brand_new_goal_id
    
    except Exception as e:
        logging.error(f'Error updating goal data in create_limbo_goal(): \n{e}')
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()
        

async def complete_limbo_goal(update, context, goal_id):
    """
    Completes a limbo goal by updating its data in the database.

    Args:
        update: Telegram update object.
        context: Telegram context object.
        goal_id: The ID of the goal to be completed.
    """
    try:
        # Retrieve the goal data from user context
        goal_data = context.user_data.get("goals", {}).get(goal_id, {})      

        if not goal_data:
            await update.message.reply_text("No data found for this goal in user context.")
            return
        goal_recurrence_type = goal_data.get("goal_recurrence_type")
        if goal_recurrence_type == "recurring":
            await update.message.reply_text(f"Nog ffkes niet geïmplementeerrrd {PA}")
            return

        # Extract the required fields from the goal data
        kwargs = {
            "goal_recurrence_type": goal_data.get("goal_recurrence_type"),
            "goal_timeframe": goal_data.get("goal_timeframe"),
            "goal_value": goal_data.get("goal_value"),
            "description": goal_data.get("description"),
            "deadline": goal_data.get("evaluation_deadline"),
            "interval": goal_data.get("interval"),
            "reminder_time": goal_data.get("reminder"),
            "reminder_scheduled": goal_data.get("schedule_reminder"),
            "time_investment_value": goal_data.get("time_investment_value"),
            "difficulty_multiplier": goal_data.get("difficulty_multiplier"),
            "impact_multiplier": goal_data.get("impact_multiplier"),
            "penalty": goal_data.get("penalty"),
            "goal_category": goal_data.get("goal_category"),
            "set_time": datetime.now(tz=BERLIN_TZ),  # Set the current time for when the goal is first fully recorded (update later if accepted)
        }
        
        

        # Update the goal data in the database
        await update_goal_data(goal_id, **kwargs)

        # Notify the user of success
        await update.message.reply_text(f"Limbo Goal with ID {goal_id} has been successfully created in the Database! {PA}")

    except Exception as e:
        logging.error(f"Error in complete_limbo_goal(): \n{e}")
        await update.message.reply_text("An error occurred while completing the goal. Please try again.")



    



        

# SETUP AND CREATION \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ 

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
                first_name TEXT DEFAULT 'Josefientje',
                pending_goals INT DEFAULT 0,
                finished_goals INT DEFAULT 0,
                failed_goals INT DEFAULT 0,       
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
                status TEXT DEFAULT 'limbo' CHECK (status IN (
                    'limbo', 'prepared', 'pending', 'paused', 'archived_done', 'archived_failed', 'archived_canceled'
                )),
		        goal_recurrence_type TEXT DEFAULT NULL,
                goal_timeframe TEXT DEFAULT NULL,       
                goal_value FLOAT DEFAULT NULL,   
                description TEXT DEFAULT NULL,
                set_time TIMESTAMPTZ DEFAULT NOW(),       -- Time when the (limbo first, then other status again) goal was set
                deadline TIMESTAMPTZ,
                interval TEXT DEFAULT NULL,
                reminder_time TIMESTAMPTZ DEFAULT NULL,       
                reminder_scheduled BOOLEAN DEFAULT False,
                time_investment_value FLOAT DEFAULT NULL,    
		        difficulty_multiplier FLOAT DEFAULT NULL,
		        impact_multiplier FLOAT DEFAULT NULL,
                penalty FLOAT DEFAULT 0,       
                iteration INTEGER DEFAULT 1,            -- N+1, either for tracking attempts at one-time goals (retries), or index of recurring
                final_iteration TEXT DEFAULT 'not_applicable',  -- The last iteration of a recurring goal. Can be used to prompt evaluation of extension ('not_applicable', 'yes', 'not yet')
                goal_category TEXT[] DEFAULT NULL,            -- eg work, productivity, chores, relationships, hobbies, self-development, wealth, impact (EA), health, fun, other       
                completed_time TIMESTAMPTZ DEFAULT NULL,                           -- Time when the goal was completed
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
            last_reset_time TIMESTAMPTZ DEFAULT %s
            )
        ''', (four_am_last_night,))
        conn.commit()

        # Add missing columns
        add_missing_columns(cursor, conn, 'manon_users', desired_columns_manon_users)
        conn.commit()

        #4 goal history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS manon_goal_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT,
            chat_id BIGINT,
            goal_text TEXT NOT NULL,
            completion_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            goal_type TEXT NOT NULL DEFAULT 'personal', -- 'personal' or 'challenges'
            challenge_from BIGINT,  -- NULL for personal goals, user_id of challenger for challenges
            FOREIGN KEY (user_id, chat_id) REFERENCES manon_users(user_id, chat_id) ON DELETE CASCADE,
            FOREIGN KEY (challenge_from, chat_id) REFERENCES manon_users(user_id, chat_id) ON DELETE CASCADE
        );
        ''')
        conn.commit()
    
        #5 polls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manon_polls (
            chat_id BIGINT NOT NULL,
            poll_id VARCHAR(255) NOT NULL,
            message_id BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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


async def register_user(context, user_id, chat_id):
    try:
        first_name = await get_first_name(context, user_id)
        conn = get_database_connection()
        cursor = conn.cursor()
        # Check if the user already exists in the users table
        cursor.execute("SELECT first_name FROM manon_users WHERE user_id = %s AND chat_id = %s", (user_id, chat_id))
        result = cursor.fetchone()

        if result is None:
            # User doesn't exist, insert with first_name
            
            cursor.execute("""
                INSERT INTO manon_users (user_id, chat_id, first_name)
                VALUES (%s, %s, %s)
            """, (user_id, chat_id, first_name))
            logging.warning(f"Inserted new user with user_id: {user_id}, chat_id: {chat_id}, first_name: {first_name}")
        elif result[0] is None:
            # User exists but first_name is missing, update it
            cursor.execute("""
                UPDATE manon_users
                SET first_name = %s
                WHERE user_id = %s AND chat_id = %s
            """, (first_name, user_id, chat_id))
            logging.warning(f"Updated first_name for user_id: {user_id}, chat_id: {chat_id} to {first_name}")
        else: 
            return f"Registered user {first_name} called /start"
        conn.commit()

    except Exception as e:
        print(f"Error updating user record: {e}")
    finally:
        cursor.close()
        conn.close() 
        

async def adjust_penalty_or_goal_value(update, context, goal_id, action, direction):
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
   
        # Step 1: Retrieve the current value of the column
        cursor.execute(f"SELECT {action} FROM manon_goals WHERE goal_id = %s", (goal_id,))
        current_value = cursor.fetchone()
        
        if current_value is None:
            logging.error(f"No value found for goal_id: {goal_id} in column: {action}")
            return None

        current_value = current_value[0]  # Unpack the fetched value
        logging.info(f"{action} value of           {current_value} retrieved")
        
        # Step 2: Calculate the new value
        if direction == "up":
            new_value = round(current_value * 1.4, 2)
        elif direction == "down":
            new_value = round(current_value * 0.6, 2)
        else:
            logging.error(f"Invalid direction: {direction}")
            return None
        
        # Ensure the new value is not less than 1
        if new_value < 1:
            new_value = 0

        # Step 3: Update the database with the new value
        cursor.execute(f"UPDATE manon_goals SET {action} = %s WHERE goal_id = %s", (new_value, goal_id))
        
        # Step 4: Commit the changes
        conn.commit()
        logging.info(f"{action} for goal_id {goal_id} updated to {new_value}")
        
        return new_value
    
    except Exception as e:
        logging.error(f'Error in adjust_penalty_or_goal_value(): \n{e}')
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()