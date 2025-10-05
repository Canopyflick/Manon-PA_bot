# Personal Assistant Telegram Bot (PA_bot) 🤖

A sophisticated Telegram bot that helps users manage their goals, track progress, and maintain accountability through gamification. Named "Manon" in production, this bot acts as a personal assistant with goal-setting, reminder systems, and comprehensive statistics tracking.

## 🎯 Core Features

### Goal Management System
- **Smart Goal Creation**: Natural language processing for goal interpretation
- **Goal Categories**: Work, productivity, chores, relationships, hobbies, self-development, money, impact, health, fun
- **Flexible Deadlines**: Support for recurring goals with custom timeframes
- **Gamification**: Point system with rewards and penalties based on goal completion
- **Status Tracking**: `limbo` → `prepared` → `pending` → `archived_done/failed/canceled`

### Statistics & Analytics
- **Daily Snapshots**: Automatic midnight captures of user progress
- **Multi-timeframe Analysis**: Weekly, monthly, quarterly, and yearly trends  
- **Comprehensive Metrics**: Completion rates, points gained, penalties, goal velocity
- **Performance Trends**: Visual indicators showing improvement/decline patterns

### Scheduling & Reminders
- **Morning Messages**: Daily goal summaries and motivational content
- **Evening Messages**: Progress reviews and next-day planning
- **Custom Reminders**: User-scheduled notifications with flexible timing
- **Bitcoin Monitoring**: Price alerts and market updates

### AI Integration
- **OpenAI Integration**: Smart goal processing and natural language understanding
- **Multiple Models**: Support for different AI models (including o1)
- **LangChain Integration**: Advanced prompt engineering and structured outputs
- **Voice Message Support**: Audio input processing

## 🏗️ Architecture

### Data Models (Refactored to Dataclasses)
- **`User`**: User profiles, scores, inventory, preferences
- **`Goal`**: Goal entities with full lifecycle management
- **`StatsSnapshot`**: Periodic performance capture for analytics
- **`GoalsReport`**: Formatted reporting structures
- **`Bitcoin`**: Market data tracking

### Database Schema
- **PostgreSQL**: Primary data store with timezone-aware operations
- **Connection Pooling**: AsyncPG for high-performance async operations
- **Tables**:
  - `manon_users`: User profiles and aggregate stats
  - `manon_goals`: Individual goals with full metadata
  - `manon_stats_snapshots`: Daily performance snapshots
  - `manon_reminders`: Scheduled notification system

### Bot Framework
- **python-telegram-bot**: Modern async Telegram API integration
- **Command System**: Modular command handlers with flexible routing
- **Message Processing**: Context-aware message analysis and responses
- **Interactive Elements**: Callback buttons for goal management

## 🚀 Current Status

### ✅ Working Features
- Goal creation and management
- User registration and profiles
- Morning/evening message scheduling
- Basic command system
- Database operations with proper data classes
- Bitcoin price monitoring
- Voice message processing

### 🔧 In Progress (Refactoring)
- **Data Class Migration**: Converting legacy dict-based operations to proper dataclasses
- **Stats System**: Comprehensive analytics dashboard (currently experiencing issues)
- **Code Organization**: Modular feature separation

### 🐛 Known Issues
- Stats feature not working properly (main focus for fixing)
- Some legacy code patterns mixed with new dataclass approach

## 📁 Project Structure

```
PA_bot/
├── features/           # Modular feature implementations
│   ├── goals/         # Goal management system
│   ├── stats/         # Analytics and reporting (NEEDS FIX)
│   ├── morning_message/   # Daily motivation
│   ├── evening_message/   # Progress reviews
│   ├── reminders/     # Notification system
│   ├── bitcoin/       # Market monitoring
│   └── ...
├── models/            # Data classes (NEW APPROACH)
│   ├── user.py
│   ├── goal.py
│   ├── stats_snapshot.py
│   └── ...
├── utils/             # Core utilities
│   ├── db.py          # Database operations
│   ├── environment_vars.py  # Configuration management
│   └── ...
├── LLMs/              # AI integration
└── main.py            # Application entry point
```

## 🛠️ Development Environment

### Prerequisites
- Python 3.9+
- PostgreSQL database
- Telegram Bot API token
- OpenAI API key

### Environment Variables
```env
ENV_MODE=dev|prod
TELEGRAM_API_KEY=your_telegram_bot_token
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://user:pass@host/db
LANGCHAIN_API_KEY=your_langchain_key
```

### Installation
```bash
git clone https://github.com/Canopyflick/Manon-PA_bot.git
cd PA_bot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.template .env  # Configure your environment
python main.py
```

## 🎮 Usage

### Basic Commands
- `/start` - Register and begin using the bot
- `/help` - Show available commands
- `/stats` - Display performance analytics (CURRENTLY BROKEN)
- `/today` - Show today's goals
- `/profile` - User profile and score
- `/wassup` - Casual greeting and status

### Goal Management
- Natural language: "I want to finish my report by 5pm"
- Quick format: "30min workout @gym"
- Recurring: "Daily meditation for 10 minutes"

### Advanced Features
- `/smarter <query>` - AI-powered assistance
- `/bitcoin` - Current BTC price
- `/dice` - Random decisions
- Voice messages for hands-free interaction

## 🔧 Technical Debt & Refactoring Notes

### Migration Strategy
1. ✅ **Phase 1**: Implement proper data classes
2. 🔄 **Phase 2**: Migrate all database operations to use data classes
3. ⏳ **Phase 3**: Fix stats system with new architecture
4. ⏳ **Phase 4**: Optimize performance and clean up legacy code

### Code Quality Improvements
- Consistent error handling patterns
- Proper async/await usage throughout
- Type hints and documentation
- Test coverage (currently minimal)

## 🚨 Priority Issues

1. **Stats Feature Broken**: The comprehensive statistics system needs debugging
2. **Data Consistency**: Ensure all operations use new dataclass models
3. **Error Handling**: Improve robustness of database operations
4. **Performance**: Optimize queries and reduce response times

## 📈 Future Roadmap

- [ ] Web dashboard for goal visualization
- [ ] Integration with external calendars
- [ ] Team/group goal management
- [ ] Machine learning for goal success prediction
- [ ] Mobile app companion
- [ ] Export functionality for personal data

---

**Bot Avatar**: 🎭 (PA variable)  
**Primary User**: Ben (working towards productivity and goal achievement)  
**Development Philosophy**: Iterative improvement with user-centric design