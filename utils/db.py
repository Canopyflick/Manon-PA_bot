from reprlib import recursive_repr
from utils.helpers import add_user_context_to_goals, datetime, timedelta, BERLIN_TZ, PA
import logging, asyncpg, os, re, pytz
from contextlib import asynccontextmanager
from dateutil.parser import parse
from datetime import time  


# Initialization of connection and database tables
# create a pool during application startup
def redact_password(url):
    # Match the "username:password@" part and redact the password
    return re.sub(r":([^:@]*)@", r":*****@", url)


class Database:
    _pool = None
    
    @classmethod
    async def initialize(cls):
        if cls._pool is not None:
            return
            
        DATABASE_URL = os.getenv('LOCAL_DB_URL', os.getenv('DATABASE_URL'))
        if not DATABASE_URL:
            raise ValueError("Database URL not found!")
        
        # Create custom timestamp codec
        def timestamp_converter(value):
            if value is not None:
                # Ensure we have a datetime object
                if isinstance(value, str):
                    # Parse string to datetime if needed
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if value.tzinfo is None:
                    # If naive datetime, assume UTC
                    value = pytz.UTC.localize(value)
                # Convert to Berlin timezone
                return value.astimezone(BERLIN_TZ)
            return value

        # Create pool only once with all settings
        cls._pool = await asyncpg.create_pool(
            DATABASE_URL,
            ssl='require' if os.getenv('HEROKU_ENV') else None,
            min_size=5,
            max_size=20,
            server_settings={'timezone': 'Europe/Berlin'},
            command_timeout=60,
            init=lambda conn: conn.set_type_codec(
                'timestamptz',
                encoder=lambda value: value,
                decoder=timestamp_converter,
                schema='pg_catalog'
            )
        )
        
        # Test the connection and verify timezone
        async with cls._pool.acquire() as conn:
            # Test basic connectivity
            await conn.execute('SELECT 1')
            
            # Verify timezone settings
            timezone = await conn.fetchval('SHOW timezone')
            logging.info(f"Database timezone set to: {timezone}")
            
            # Optional: Set session timezone explicitly
            await conn.execute("SET timezone TO 'Europe/Berlin'")
            
            # Verify the timezone setting worked
            test_time = await conn.fetchval('SELECT NOW()')
            logging.info(f"Current database time: {test_time}")

        logging.info("Database connection successful with timezone configuration")

    @classmethod
    def acquire(cls):
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized!")
        return cls._pool.acquire()

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None




# Function to add missing columns
async def add_missing_columns(conn, table_name: str, desired_columns: dict):
    """Add missing columns to the specified table"""
    try:
        # Get existing columns
        existing_columns = await conn.fetch('''
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = $1
        ''', table_name)
        
        existing_column_names = {col['column_name'] for col in existing_columns}

        # Add missing columns
        for col_name, col_type in desired_columns.items():
            if col_name not in existing_column_names:
                await conn.execute(f'''
                    ALTER TABLE {table_name} 
                    ADD COLUMN {col_name} {col_type}
                ''')
                logging.warning(f"Added column {col_name} to {table_name}")

    except Exception as e:
        logging.error(f"Error adding columns to {table_name}: {e}")
        raise            


async def setup_database():
    """Create or update database tables"""
    try:    
        async with Database.acquire() as conn:

        #1 manon_users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS manon_users (
                    user_id BIGINT,
                    chat_id BIGINT,
                    first_name TEXT DEFAULT 'Josefientje',
                    pending_goals INT DEFAULT 0,
                    finished_goals INT DEFAULT 0,
                    failed_goals INT DEFAULT 0,       
                    score FLOAT DEFAULT 0,
                    penalties_accrued FLOAT DEFAULT 0,          
                    inventory JSONB DEFAULT '{"boosts": 1, "challenges": 1, "links": 1}',
                    any_reminder_scheduled BOOLEAN DEFAULT False,
                    long_term_goals TEXT DEFAULT NULL,       
                    PRIMARY KEY (user_id, chat_id)
                )
            ''')
            # Desired columns with definitions
            desired_columns_manon_users = {
                'user_id': 'BIGINT',
                'chat_id': 'BIGINT',
            }
            await add_missing_columns(conn, 'manon_users', desired_columns_manon_users)

    
            #2 manon_goals table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS manon_goals (
                    goal_id SERIAL PRIMARY KEY,
                    group_id BIGINT DEFAULT NULL,           -- Group ID for recurring goals       
                    user_id BIGINT NOT NULL,                -- Foreign key to identify the user
                    chat_id BIGINT NOT NULL,                -- Foreign key to identify the chat 
                    status TEXT DEFAULT 'limbo' CHECK (status IN (
                        'limbo', 'prepared', 'pending', 'paused', 'archived_done', 'archived_failed', 'archived_canceled'
                    )),
		            recurrence_type TEXT DEFAULT NULL,
                    timeframe TEXT DEFAULT NULL,       
                    goal_value FLOAT DEFAULT NULL,   
                    total_goal_value FLOAT DEFAULT NULL,       
                    goal_description TEXT DEFAULT NULL,
                    set_time TIMESTAMPTZ DEFAULT NOW(),       -- Time when the (limbo first, then other status again) goal was set
                    deadline TIMESTAMPTZ,
                    deadlines TEXT[] DEFAULT NULL,              -- To use for the goal_proposal template, storing future and past deadlines of the entire group_id as well 
                    interval TEXT DEFAULT NULL,
                    reminder_time TIMESTAMPTZ DEFAULT NULL,
                    reminders_times TEXT[] DEFAULT NULL,       -- To use for the goal_proposal template, storing future and past reminders of the entire group_id as well
                    reminder_scheduled BOOLEAN DEFAULT False,   
                    time_investment_value FLOAT DEFAULT NULL,    
		            difficulty_multiplier FLOAT DEFAULT NULL,
		            impact_multiplier FLOAT DEFAULT NULL,
                    penalty FLOAT DEFAULT NULL,
                    total_penalty FLOAT DEFAULT NULL,
                    attempt INTEGER DEFAULT 1,                      -- N+1, for tracking attempts (retries)
                    iteration INTEGER DEFAULT NULL,                 -- N+1 iteration of instances of individual (sub)goals that belong to the same group of one recurring goal
                    final_iteration TEXT DEFAULT 'not applicable',  -- The last in the series of this group_id: final iteration of this recurring goal. Can be used to prompt evaluation of extension ('not applicable', 'yes', 'not yet')
                    goal_category TEXT[] DEFAULT NULL,            -- eg work, productivity, chores, relationships, hobbies, self-development, wealth, impact (EA), health, fun, other       
                    completion_time TIMESTAMPTZ DEFAULT NULL,                           -- Time when the goal was completed
                    FOREIGN KEY (user_id, chat_id) REFERENCES manon_users (user_id, chat_id)
                )
            ''')
            desired_columns_manon_goals = {
                'goal_id': 'SERIAL PRIMARY KEY',
                'attempt': 'INTEGER DEFAULT 1',
                'iteration': 'INTEGER DEFAULT NULL',
                'final_iteration': 'TEXT DEFAULT "not applicable"' 
            }
            await add_missing_columns(conn, 'manon_goals', desired_columns_manon_goals)
            
            #3 manon_reminders table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS manon_reminders (
                    reminder_id SERIAL PRIMARY KEY, 
                    user_id BIGINT NOT NULL,                -- Foreign key to identify the user
                    chat_id BIGINT NOT NULL,                -- Foreign key to identify the chat       
                    reminder_text TEXT DEFAULT NULL,
                    reminder_category TEXT[] DEFAULT NULL,       
                    set_time TIMESTAMPTZ DEFAULT NOW(),       -- Time when the reminder was set/requested
                    time TIMESTAMPTZ DEFAULT NULL,
                    FOREIGN KEY (user_id, chat_id) REFERENCES manon_users (user_id, chat_id)
                )
            ''')
            desired_columns_manon_reminders = {
                'reminder_id': 'SERIAL PRIMARY KEY',
                'user_id': 'BIGINT NOT NULL'
            }
            await add_missing_columns(conn, 'manon_reminders', desired_columns_manon_reminders)

            #4 stats_snapshots table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS stats_snapshots (
                    snapshot_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,                -- Foreign key to identify the user
                    chat_id BIGINT NOT NULL,                -- Foreign key to identify the chat
                    date DATE NOT NULL,                     -- Date of the snapshot (without time)
        
                    -- Daily counts
                    goals_set INTEGER DEFAULT 0,            -- Number of goals set on this date
                    goals_finished INTEGER DEFAULT 0,       -- Number of goals completed on this date
                    goals_failed INTEGER DEFAULT 0,         -- Number of goals failed on this date
                    goals_pending INTEGER DEFAULT 0,        -- Number of goals still pending at snapshot time
        
                    -- Value metrics
                    score_gained FLOAT DEFAULT 0,           -- Score earned on this date
                    penalties_incurred FLOAT DEFAULT 0,     -- Penalties accrued on this date
                    completion_rate FLOAT DEFAULT NULL,     -- Daily completion rate (percentage)
        
                    -- Time-based metrics
                    avg_completion_time INTERVAL DEFAULT NULL,  -- Average time to complete goals on this date
                    total_time_invested INTERVAL DEFAULT NULL,  -- Total time invested in goals on this date
        
                    -- Categories snapshot (optional, for future use)
                    category_distribution JSONB DEFAULT NULL,   -- Distribution of goals across categories
        
                    -- Metadata
                    snapshot_time TIMESTAMPTZ DEFAULT NOW(),   -- Exact time when snapshot was taken
        
                    FOREIGN KEY (user_id, chat_id) REFERENCES manon_users (user_id, chat_id),
                    UNIQUE (user_id, chat_id, date)           -- Ensure one snapshot per user per day
                )
            ''')
            desired_columns_stats_snapshots = {
                'snapshot_id': 'SERIAL PRIMARY KEY',
                'user_id': 'BIGINT NOT NULL',
                'chat_id': 'BIGINT NOT NULL',
                'date': 'DATE NOT NULL'
            }
            await add_missing_columns(conn, 'stats_snapshots', desired_columns_stats_snapshots)

            # Create index for faster queries
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_stats_snapshots_user_date 
                ON stats_snapshots (user_id, chat_id, date);
            ''')

        logging.info("Database tables initialized successfully")

    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        raise
# End of setup /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\












# Database-related functions \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/   
def format_array_for_postgres(py_list):
    if not py_list:
        return None
    return '{' + ','.join(f'"{item}"' for item in py_list) + '}'

async def update_goal_data(goal_id, initial_update=False, **kwargs):
    if not kwargs:
        logging.warning(f"{PA} No updates provided to update_goal_data()")
        return
        
    try:
        # Add group_id dynamically for recurring goals, upon first update
        if initial_update and kwargs.get("recurrence_type") == "recurring":
            kwargs["group_id"] = goal_id
            kwargs["final_iteration"] = "not yet"
            
        # Convert datetime objects to ISO format strings
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                kwargs[key] = value.isoformat()

        # Handle arrays properly
        if 'goal_category' in kwargs and isinstance(kwargs['goal_category'], list):
            kwargs['goal_category'] = list(filter(None, kwargs['goal_category']))  # Remove any None values

        # Handle special expressions for SQL updates
        special_updates = []
        if "increment_attempt" in kwargs:
            special_updates.append("attempt = attempt + 1")
            del kwargs["increment_attempt"]

            
        regular_updates = ', '.join(f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys()))
        updates = ', '.join(filter(None, [regular_updates] + special_updates))
        
        values = [goal_id] + list(kwargs.values())  # goal_id first, then kwargs values
        

        query = f'''
            UPDATE manon_goals
            SET {updates}
            WHERE goal_id = $1
        '''
        
        logging.debug(f"Query: {query}")
        logging.debug(f"Values: {values}")
        
        async with Database.acquire() as conn:
            await conn.execute(query, *values)
        
    except Exception as e:
        logging.error(f'Error updating goal data for goal_id {goal_id}: {e}')
        logging.error(f'Failed query: {query}')
        logging.error(f'Values: {values}')
        raise
    

async def update_user_data(user_id, chat_id, **kwargs):
    """
    Updates user data in the manon_users table.

    Args:
        user_id (int): The ID of the user to update.
        chat_id (int): The chat ID associated with the user.
        kwargs: Key-value pairs of columns to update. Supports special keys like 'increment_*' for increments.

    Raises:
        Exception: If an error occurs during the update.
    """
    if not kwargs:
        logging.warning("No updates provided to update_user_data()")
        return

    try:
        # Handle special increments (e.g., increment_pending_goals, increment_finished_goals, etc.)
        special_updates = []
        keys_to_remove = []
        for key in kwargs.keys():
            if key.startswith("increment_"):
                column_name = key.replace("increment_", "")
                increment_value = kwargs.get(key, 1)  # Default to 1 if no value is provided
                special_updates.append(f"{column_name} = {column_name} + {increment_value}")
                keys_to_remove.append(key)

        # Remove special keys from kwargs to avoid double handling
        for key in keys_to_remove:
            del kwargs[key]

        # Prepare regular updates
        regular_updates = ', '.join(f"{key} = ${i+3}" for i, key in enumerate(kwargs.keys()))
        updates = ', '.join(filter(None, [regular_updates] + special_updates))

        # Build the query and values
        values = [user_id, chat_id] + list(kwargs.values())
        query = f'''
            UPDATE manon_users
            SET {updates}
            WHERE user_id = $1 AND chat_id = $2
        '''

        logging.debug(f"Query: {query}")
        logging.debug(f"Values: {values}")

        # Execute the query
        async with Database.acquire() as conn:
            await conn.execute(query, *values)

    except Exception as e:
        logging.error(f"Error updating user data for user_id {user_id} and chat_id {chat_id}: {e}")
        logging.error(f"Failed query: {query}")
        logging.error(f"Values: {values}")
        raise

        
        
async def create_limbo_goal(update, context):
    chat_id=update.effective_chat.id
    user_id = update.effective_user.id
    try:
        async with Database.acquire() as conn:
            brand_new_goal_id = await conn.fetchval('''
                INSERT INTO manon_goals (
                    user_id,
                    chat_id,
                    status
                ) VALUES ($1, $2, $3)
                RETURNING goal_id;
            ''', user_id, chat_id, 'limbo')
            
            logging.info(f"\nNew Limbo Goal Created: {brand_new_goal_id}\n")
        
        return brand_new_goal_id
    
    except asyncpg.PostgresError as e:
        logging.error(f'Database error in create_limbo_goal(): \n{e}')
        return None
    except Exception as e:
        logging.error(f'Unexpected error in create_limbo_goal(): \n{e}')
        return None
    

async def create_recurring_goal_instance(**kwargs):
    try:
        async with Database.acquire() as conn:
            # Dynamically build the query based on kwargs
            columns = ', '.join(kwargs.keys())  # Extract column names
            placeholders = ', '.join(f'${i+1}' for i in range(len(kwargs)))  # Create $1, $2, ..., $N placeholders
            values = list(kwargs.values())  # Extract values

            query = f'''
                INSERT INTO manon_goals ({columns})
                VALUES ({placeholders})
                RETURNING goal_id;
            '''
            # Execute the query
            brand_new_goal_id = await conn.fetchval(query, *values)

            logging.info(f"New goal created with ID: {brand_new_goal_id}")
            return brand_new_goal_id

    except asyncpg.PostgresError as e:
        logging.error(f"Database error in create_recurring_goal_instance: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in create_recurring_goal_instance: {e}")
        return None

        

async def complete_limbo_goal(update, context, goal_id, initial_update=True):
    chat_id=update.effective_chat.id
    """
    Completes a limbo goal's records in the database (should only have a goal_id and status as of yet, was only created a few seconds ago).

    Args:
        update: Telegram update object.
        context: Telegram context object.
        goal_id: The ID of the goal to be completed.
    """
    try:
        # Retrieve the goal data from user context
        goal_data = context.user_data["goals"].get(goal_id)     

        if not goal_data:
            logging.critical(f"💩 Couldn't complete limbo goal for {goal_id}. (No data found for this goal in user context)'")
            await update.message.reply_text("No data found for this goal in user context.")
            return
        
       
        # Extract the required fields from the goal data, same whether initial update or not:
        kwargs = {
            "recurrence_type": goal_data.get("recurrence_type"),
            "timeframe": goal_data.get("timeframe"),
            "goal_value": goal_data.get("goal_value"),
            "reminder_scheduled": goal_data.get("schedule_reminder", goal_data.get("reminder_scheduled")), # fallback is for adjustment cases, where reminder_scheduled is already the name of the key that's used
            "goal_description": goal_data.get("goal_description"),           
            "penalty": goal_data.get("penalty"),
            "reminders_times": goal_data.get("reminders_times"),
            "group_id": (goal_data.get("group_id")) if goal_data.get("group_id") else None,
        }

        if initial_update:      # All of these aren't changed during adjustments
            kwargs["deadline"] = goal_data.get("evaluation_deadline") if goal_data.get("evaluation_deadline") else None
            kwargs["deadlines"] = goal_data.get("evaluation_deadlines") if goal_data.get("evaluation_deadlines") else None
            kwargs["total_goal_value"] = goal_data.get("total_goal_value")
            kwargs["total_penalty"] = goal_data.get("total_penalty")
            kwargs["interval"] = goal_data.get("interval")
            kwargs["reminder_time"] = goal_data.get("reminder_time") if goal_data.get("reminder_time") else None
            kwargs["reminders_times"] = goal_data.get("reminders_times")
            kwargs["time_investment_value"] = goal_data.get("time_investment_value")
            kwargs["difficulty_multiplier"] = goal_data.get("difficulty_multiplier")
            kwargs["impact_multiplier"] = goal_data.get("impact_multiplier")
            kwargs["goal_category"] = goal_data.get("category")
            kwargs["set_time"] = datetime.now(tz=BERLIN_TZ)  # Set the current time for when the goal is first fully recorded

        if not initial_update:  # upon adjustments, deadlines and reminders are all put into the same field, so need to get distinguished here based on recurrence_type of goal
            reminders = goal_data.get("reminders_times", [])
            reminders_count = len(reminders) if isinstance(reminders, list) else 0
            if reminders_count == 1:
                kwargs["reminder_time"] = goal_data.get("reminders_times")
            if reminders_count > 1:
                kwargs["reminders_times"] = goal_data.get("reminders_times")
     
            recurrence_type = goal_data.get("recurrence_type")
            if recurrence_type == "recurring":
                kwargs["deadlines"] = goal_data.get("deadlines")
            else:
                kwargs["deadline"] = goal_data.get("deadlines")             

        # Update the goal data in the database
        await update_goal_data(goal_id, initial_update, **kwargs)
        
        # Validate goal constraints
        if initial_update:      # don't know how to make this work for adjustments yet (would have to update the function I think and account for initial_update value inside it)
            async with Database.acquire() as conn:
                validation_result = await validate_goal_constraints(goal_id, conn)
                if not validation_result['valid']:
                    error_msg = f"{PA} Goal ID {goal_id} has issues:\n{validation_result['errors']}"
                    logging.error(error_msg)
                    await context.bot.send_message(chat_id=chat_id, text=f"{error_msg}")
                    return

        # Notify the user of success
        await update.message.reply_text(
            f"Limbo Goal with ID {goal_id} has been successfully "
            f"{'created' if initial_update else 'updated'} in the Database! {PA}"
        )

    except Exception as e:
        logging.error(f'Unexpected error in complete_limbo_goal(): \n{e}')
        return None


# Dummy function, not yet interacting with db        
async def fetch_long_term_goals(chat_id, user_id):
    return "To be increasingly kind and useful to others. To set myself up for continuous learning, self-improvement, longevity and rich relationships."


async def register_user(context, user_id, chat_id):
    try:
        first_name = await get_first_name(context, user_id, chat_id)
        
        async with Database.acquire() as conn:
            # Check if the user already exists in the users table
            result = await conn.fetchrow(
                "SELECT first_name FROM manon_users WHERE user_id = $1 AND chat_id = $2",
                user_id, chat_id
            )

            if result is None:
                # User doesn't exist, insert with first_name
                await conn.execute("""
                    INSERT INTO manon_users (user_id, chat_id, first_name)
                    VALUES ($1, $2, $3)
                """, user_id, chat_id, first_name)
                logging.warning(f"Inserted new user with user_id: {user_id}, chat_id: {chat_id}, first_name: {first_name}")
                await context.bot.send_message(chat_id, text=f"_Registered new user,_ *{first_name}*_, with User ID:_", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text=f"_{user_id}_", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text="_in chat:_", parse_mode="Markdown")
                await context.bot.send_message(chat_id, text=f"_{chat_id}_", parse_mode="Markdown")
            elif result['first_name'] is None:
                # User exists but first_name is missing, update it
                await conn.execute("""
                    UPDATE manon_users
                    SET first_name = $1
                    WHERE user_id = $2 AND chat_id = $3
                """, first_name, user_id, chat_id)
                logging.warning(f"Updated first_name for user_id: {user_id}, chat_id: {chat_id} to {first_name}")
            
            else:
                return f"Registered user {first_name} called /start"

    except Exception as e:
        logging.error(f"Error updating user record: {e}")  
        raise  
        

async def adjust_penalty_or_goal_value(update, context, goal_id, action, direction):
    try:
        async with Database.acquire() as conn:
            # Step 1: Retrieve the current value of the column
            current_value = await conn.fetchval(
                f"SELECT {action} FROM manon_goals WHERE goal_id = $1",
                goal_id
            )
            
            if current_value is None:
                logging.error(f"No value found for goal_id: {goal_id} in column: {action}")
                return None

            logging.info(f"{action} value of {current_value} retrieved")

            new_value = None 
            if current_value <= 5:   # move in increments of 1 for low values
                if direction == "up":
                    new_value = current_value + 1
                elif direction == "down":
                    new_value = current_value - 1 
            elif current_value > 5:
                if direction == "up":
                    new_value = current_value * 1.4
                elif direction == "down":
                    new_value = current_value * 0.6
            
            # Ensure the new value is not less than 1
            if new_value < 1:
                new_value = 0            

            # Step 3: Update the database with the new value
            await conn.execute(
                f"UPDATE manon_goals SET {action} = $1 WHERE goal_id = $2",
                new_value, goal_id
            )
            
            logging.info(f"{action} for goal_id {goal_id} {current_value} updated to {new_value}")
            
            new_value = round(new_value, 1)
            return new_value
    
    except Exception as e:
        logging.error(f'Error in adjust_penalty_or_goal_value(): \n{e}')
        return None
    
# incorrect query still        
async def fetch_template_data_from_db(context, goal_id):
    try:
        async with Database.acquire() as conn:
            # Fetch the data for the given goal_id
            query = '''
            SELECT 
                recurrence_type,
                goal_description,
                deadline,
                deadlines,
                goal_value,
                total_goal_value,
                penalty,
                total_penalty,
                reminder_scheduled AS schedule_reminder,
                array_length(reminders_times, 1) AS reminder_count,
                reminders_times,
                time_investment_value,
                difficulty_multiplier
            FROM manon_goals
            WHERE goal_id = $1
            '''
            result = await conn.fetchrow(query, goal_id)
            
            if not result:
                raise ValueError(f"No goal found for goal_id: {goal_id}")

            kwargs = dict(result)
            
            # if recurrence_type =="recurring":
            #     goal_id = group_id      # maybe not essential, but might as well put it as a placeholder here to keep in mind for later that potentially ALL goal_ids with this group_id should be adjusted, for cases where the goal is not in limbo anymore and was already split up in deadlinte_count*N unique goals. Ah yes and ALL deadlines are only stored in the initial goal_id, the mother_goal_id which == group_id, so that IS the one we need to use for adjustments usuallyyyyyy, unless ... well think about this more later XXX
            await add_user_context_to_goals(context, goal_id, **kwargs)
            
            return kwargs
    
    except Exception as e:
        logging.error(f'{PA} Error in fetch_template_data_from_db(): \n{e}')
        return None
    

async def validate_goal_constraints(goal_id: int, conn) -> dict:
    """
    Validates a goal's data against predefined constraints.
    
    Args:
        goal_id (int): The ID of the goal to validate.
        conn (asyncpg connection): The database connection.

    Returns:
        dict: A dictionary with validation results and messages.
    """
    # Get goal data
    goal_record = await conn.fetchrow('''
        SELECT * FROM manon_goals WHERE goal_id = $1;
    ''', goal_id)

    if not goal_record:
        return {'valid': False, 'message': 'Goal not found.'}

    # Convert record to dictionary
    goal_data = dict(goal_record)
    
    errors = []

    # Validation rules
    if goal_data['status'] not in ('limbo', 'prepared', 'pending', 'paused', 'archived_done', 'archived_failed', 'archived_canceled', None):
        errors.append('Invalid status value.')

    if goal_data['recurrence_type'] not in ('one-time', 'recurring', None):
        errors.append('Invalid recurrence type.')

    if goal_data['timeframe'] not in ('today', 'by_date', 'open-ended', None):
        errors.append('Invalid timeframe.')

    if goal_data['timeframe'] in ('today', 'by_date') and not goal_data['deadline'] and goal_data['recurrence_type'] != "recurring":
        errors.append('Deadline for one-time goals must be set for "today" or "by_date" timeframes (cannot be "open-ended" or other values).')

    if goal_data['timeframe'] == 'open-ended' and goal_data['deadline']:
        errors.append('Deadline must not be set for "open-ended" timeframe.')

    if goal_data['final_iteration'] not in ('not applicable', 'not yet', 'yes', None):
        errors.append('Invalid final iteration value.')

    if goal_data['goal_category'] is None or not isinstance(goal_data['goal_category'], list):
        errors.append('Goal category must be a non-null array.')

    # Return validation results
    if errors:
        return {'valid': False, 'errors': errors}
    return {'valid': True, 'message': 'Goal is valid.'}


async def get_first_name(context, user_id, chat_id):
    try:
        async with Database.acquire() as conn:
            query = "SELECT first_name FROM manon_users WHERE user_id = $1"
            row = await conn.fetchrow(query, user_id)
            if row and row.get("first_name"):
                return row["first_name"]
            else:
                chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                return chat_member.user.first_name
    except Exception as e:
        logging.error(f"Error fetching first name for user_id {user_id}: {e}")
        return "Valentijntje"
    


async def fetch_goal_data(goal_id, columns="*", conditions=None, single_value=False):
    """
    Fetch specified columns for a given goal_id from the manon_goals table.

    Args:
        goal_id (int): The ID of the goal to fetch data for.
        columns (str): Comma-separated column names to fetch (default is '*').
        conditions (str, optional): Additional SQL conditions to apply to the query.

    Returns:
        dict: A dictionary containing the fetched data, or simply the value if only one column is requested, or None if an error occurs.
    """
    try:
        async with Database.acquire() as conn:
            # Build the query dynamically
            base_query = f'''
                SELECT {columns}
                FROM manon_goals
                WHERE goal_id = $1
            '''
            if conditions:
                base_query += f" AND {conditions}"

            # Execute the query
            result = await conn.fetchrow(base_query, goal_id)

            if not result:
                raise ValueError(f"No data found for goal_id: {goal_id} with conditions: {conditions or 'None'}")
            
            # Return a single value if requested and a single column is being fetched
            if single_value and len(result) == 1:
                return list(result.values())[0]

            # Return the result as a dictionary
            return dict(result)

    except Exception as e:
        logging.error(f"Error in fetch_goal_data() for goal_id {goal_id}: {e}")
        return None
    

async def fetch_user_stats(update, context, user_id):
    chat_id = update.effective_chat.id
    columns = "pending_goals, finished_goals, failed_goals, score, penalties_accrued"
    
    results = await fetch_user_data(user_id, columns=columns)
    # goals_set_today = await fetch_goal_data(goal_id )
    
    next_seven_days = await fetch_upcoming_goals(chat_id, user_id, timeframe="next week")
    goals_count = next_seven_days[-1] if next_seven_days else 0 # Access the last element directly, with [-1]

    results["next_seven_days"] = goals_count
    
    return results
        
    

async def fetch_user_data(user_id, columns="*", conditions=None, single_value=False):
    """
    Fetch specified columns for a given user_id from the manon_goals table.

    Args:
        user_id (int): The ID of the goal to fetch data for.
        columns (str): Comma-separated column names to fetch (default is '*').
        conditions (str, optional): Additional SQL conditions to apply to the query.

    Returns:
        dict: A dictionary containing the fetched data, or simply the value if only one column is requested, or None if an error occurs.
    """
    try:
        async with Database.acquire() as conn:
            # Build the query dynamically
            base_query = f'''
                SELECT {columns}
                FROM manon_users
                WHERE user_id = $1
            '''
            if conditions:
                base_query += f" AND {conditions}"

            # Execute the query
            result = await conn.fetchrow(base_query, user_id)

            if not result:
                raise ValueError(f"No data found for user_id: {user_id} with conditions: {conditions or 'None'}")
            
            # Return a single value if requested and a single column is being fetched
            if single_value and len(result) == 1:
                return list(result.values())[0]

            # Return the result as a dictionary
            return dict(result)

    except Exception as e:
        logging.error(f"Error in fetch_user_data() for user_id {user_id}: {e}")
        return None


async def fetch_pending_goals_count_between_times(chat_id=None):
    """
    Fetches the count of 'pending' goals with set_time between 4 AM today and 4 AM the next day.

    Args:
        today_tz (datetime): Current datetime with timezone awareness.
        chat_id (int, optional): Filter by chat_id if provided.

    Returns:
        int: The count of matching goals.
    """
    try:
        # Define the time range (4 AM today to 4 AM the next day)
        berlin_tz = pytz.timezone("Europe/Berlin")
        today = today_tz.astimezone(berlin_tz).date()
        start_time = berlin_tz.localize(datetime.combine(today, time(4, 0, 0))) #(localize doesn't work prolly)
        end_time = start_time + timedelta(days=1)

        # Build conditions and query dynamically
        conditions = "status = 'pending' AND set_time BETWEEN $1 AND $2"
        params = [start_time, end_time]

        if chat_id:
            conditions += " AND chat_id = $3"
            params.append(chat_id)

        async with Database.acquire() as conn:
            query = f'''
                SELECT COUNT(*)
                FROM manon_goals
                WHERE {conditions}
            '''

            # Execute the query and fetch result
            result = await conn.fetchval(query, *params)
            return result

    except Exception as e:
        logging.error(f"Error in fetch_pending_goals_count_between_times(): {e}")
        return None


# fetches all pending goals today, in 1 overview (deadline between now and until {timeframe}AM tomorrow, OR 24 hours into the future, and puts them all in one message 
async def fetch_upcoming_goals(chat_id, user_id, timeframe=6):     # fetches until 6am tomorrow by default
    try:
        async with Database.acquire() as conn:
            # Prepare base query with placeholders
            base_query = '''
                SELECT 
                    goal_description, 
                    deadline, 
                    goal_value, 
                    penalty, 
                    reminder_scheduled, 
                    final_iteration
                FROM manon_goals
                WHERE chat_id = $1 
                AND user_id = $2
                AND status = 'pending'
            '''        
            
            # Dynamic time condition logic
            if timeframe == "24hs":
                time_condition = """
                AND deadline >= NOW()
                AND deadline <= NOW() + INTERVAL '24 hours'
                """
            elif timeframe == "rest_of_day":
                time_condition = """
                AND deadline >= NOW()
                AND deadline <= DATE_TRUNC('day', NOW()) + INTERVAL '28 hours'
                """
            elif timeframe == "tomorrow":
                time_condition = """
                AND deadline >= DATE_TRUNC('day', NOW() + INTERVAL '1 day') + INTERVAL '4 hours'
                AND deadline <= DATE_TRUNC('day', NOW() + INTERVAL '1 day') + INTERVAL '28 hours'
                """
            elif timeframe == "next week":
                time_condition = """
                AND deadline >= DATE_TRUNC('day', NOW())
                AND deadline < DATE_TRUNC('day', NOW() + INTERVAL '8 days') -- captures the full 7 days
                """
            else:
                time_condition = f"""
                AND deadline >= NOW()
                AND deadline <= DATE_TRUNC('day', NOW() + INTERVAL '1 day') + INTERVAL '{timeframe} hours'
                """
                
            # Build query
            query = base_query + time_condition
            params = [chat_id, user_id]
            query += " ORDER BY deadline ASC"
            logging.critical(f"Query: {query}")
            logging.critical(f"Parameters: {params}")


            # Execute the query
            rows = await conn.fetch(query, *params)

            # Format the results
            if not rows:
                logging.info(f"No rows retrieved in fetch_upcoming_goals()")
                return "You have no deadlines between now and tomorrow morning ☃️", 0, 0, 0

        upcoming_goals = []
        total_goal_value = 0
        total_penalty = 0 
        today = datetime.now(BERLIN_TZ).date()
        goals_count = 0
        for row in rows:
            goals_count += 1
            description = row["goal_description"] or "No description found... 👻"
            deadline_dt = row["deadline"].astimezone(BERLIN_TZ)
            deadline_date = deadline_dt.date()
            # Format the deadline
            if deadline_date == today:
                deadline = f"{deadline_dt.strftime('%H:%M')} today"
            else:
                deadline = f"{deadline_dt.strftime('%a %H:%M')}"
            goal_value = f"{row['goal_value']:.1f}" if row["goal_value"] is not None else "N/A"
            penalty = f"{row['penalty']:.1f}" if row["penalty"] is not None else "N/A"
            reminder = "⏰" if row["reminder_scheduled"] else ""
            final_iteration = " (❗Last in series❗)" if row["final_iteration"] == "yes" else ""
            
            total_goal_value += float(goal_value)
            total_penalty += float(penalty) 

            # Create a formatted string for each goal
            upcoming_goals.append(
                f"*{description}*{final_iteration}\n"
                f"  📅 Deadline: {deadline} {reminder}\n"
                f"  ⚡ {goal_value} | 🌚 {penalty}\n"
            )

        return "\n\n".join(upcoming_goals), round(total_goal_value, 1), round(total_penalty, 1), goals_count
    except Exception as e:
        logging.error(f"Error fetching goals for chat_id {chat_id}, user_id {user_id}: {e}")
        return "An error occurred while fetching your goals. Please try again later."
    

async def record_reminder(update, context, output):
    """Record a reminder in the manon_reminders table"""
    try:
        # Get user information
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Parse the reminder time
        try:
            reminder_time = parse(output.time)
            # Ensure the time is timezone-aware
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=BERLIN_TZ)
        except ValueError as e:
            await update.message.reply_text("Invalid time format provided.")
            logging.error(f"Time parsing error: {e}")
            return

        async with Database.acquire() as conn:
            query = """
                INSERT INTO manon_reminders 
                (user_id, chat_id, reminder_text, reminder_category, time)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING reminder_id
            """
            
            result = await conn.fetchrow(
                query,
                user_id,
                chat_id,
                output.reminder_text,
                output.reminder_category,
                reminder_time.isoformat()
            )
            
            reminder_id = result['reminder_id']

            # Format the confirmation message
            formatted_time = reminder_time.strftime("%A, %B %d, %Y at %H:%M")
            confirmation_message = (
                f"✅ Reminder #{reminder_id} set successfully!\n\n"
                f"📝 Text: {output.reminder_text}\n"
                f"🗓 Time: {formatted_time}\n"
                f"📋 Category: {output.reminder_category}"
            )

            # Send confirmation message
            await update.message.reply_text(
                confirmation_message,
                parse_mode='HTML'
            )
            
            # Schedule the reminder immediately if it's within the next 24 hours
            now = datetime.now(tz=BERLIN_TZ)
            if reminder_time <= now + timedelta(days=1):
                reminder_data = {
                    'reminder_id': reminder_id,
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'reminder_text': output.reminder_text,
                    'time': reminder_time
                }
                # Local import to avoid circular import on boot
                from utils.scheduler import scheduler
                from modules.reminders import send_reminder

                scheduler.add_job(
                    send_reminder,
                    'date',
                    run_date=reminder_time,
                    args=[context.bot, reminder_data],
                    id=f"regularreminder_{reminder_id}",
                    replace_existing=True
                )
                logging.info(f"Scheduled immediate reminder #{reminder_id} for {formatted_time}")

            return reminder_id

    except Exception as e:
        error_message = f"Failed to set reminder: {str(e)}"
        await update.message.reply_text(error_message)
        logging.error(f"Error in record_reminder: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None
    