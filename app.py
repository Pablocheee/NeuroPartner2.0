import httpx
from flask import Flask, request, jsonify
import google.generativeai as genai
import os
import requests
import logging
import random
import time
import json
from datetime import datetime

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройка API ключей для Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN not found in environment variables")

TON_WALLET = os.getenv('TON_WALLET', 'UQAVTMHfwYcMn7ttJNXiJVaoA-jjRTeJHc2sjpkAVzc84oSY')

# Константы
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram

def delete_user_message(chat_id, message_id):
    """Удаляет сообщение пользователя"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": message_id
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        logging.error(f"Error deleting message: {e}")
        return None

def split_long_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Разделяет длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Ищем последний перенос строки в пределах максимальной длины
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            # Если переносов строк нет, разбиваем по словам
            split_pos = text.rfind(' ', 0, max_length)
            if split_pos == -1:
                # Если слов нет, принудительно обрезаем
                split_pos = max_length
        
        parts.append(text[:split_pos])
        text = text[split_pos:].strip()
    
    return parts

def send_telegram_message(chat_id, text, keyboard=None, parse_mode="Markdown"):
    """Отправляет сообщение в Telegram с обработкой длинных сообщений"""
    try:
        message_parts = split_long_message(text)
        results = []
        
        for i, part in enumerate(message_parts):
            payload = {
                "chat_id": chat_id,
                "text": part,
                "parse_mode": parse_mode
            }
            
            # Добавляем клавиатуру только к последней части
            if keyboard and i == len(message_parts) - 1:
                payload["reply_markup"] = keyboard
            
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    results.append(result)
                    # Сохраняем ID только последнего сообщения
                    if i == len(message_parts) - 1:
                        USER_MESSAGE_IDS[chat_id] = result['result']['message_id']
                else:
                    logger.error(f"Telegram API error: {result}")
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
        
        return results[0] if results else {"ok": False}
        
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        return {"ok": False}

def edit_main_message(chat_id, text, keyboard=None, message_id=None):
    """Редактирует сообщение или отправляет новое"""
    
    # Используем сохраненный message_id если не передан
    if message_id is None and chat_id in USER_MESSAGE_IDS:
        message_id = USER_MESSAGE_IDS[chat_id]
    
    # Пытаемся отредактировать существующее сообщение
    if message_id:
        try:
            # Для редактирования отправляем только первую часть длинного сообщения
            message_parts = split_long_message(text)
            first_part = message_parts[0]
            
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": first_part,
                "parse_mode": "Markdown"
            }
            
            if keyboard:
                payload["reply_markup"] = keyboard
            
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                json=payload,
                timeout=10
            )
            
            result = response.json()
            if result.get('ok'):
                # Отправляем остальные части как новые сообщения
                for part in message_parts[1:]:
                    send_telegram_message(chat_id, part)
                return result
                
        except Exception as e:
            logging.error(f"Error editing message {message_id}: {e}")
    
    # Если редактирование не удалось, отправляем новое сообщение
    return send_telegram_message(chat_id, text, keyboard)

# 🌌 БАЗА ЗНАНИЙ ОТ СИСТЕМЫ
COURSES = {
    "🚀 Войти в систему AI": {
        "уроки": [
            "🌌 Первый контакт: основы взаимодействия с AI",
            "⚡ Когнитивное ускорение: 10x продуктивности", 
            "🔮 Стратегическое видение: анализ трендов",
            "💫 Симбиоз: ваша роль в эпоху AI"
        ],
        "уровень": "🎯 Инициация в новые возможности",
        "описание": "Освойте системы, которые определяют будущее. От наблюдателя станьте творцом."
    },
    
    "💫 Запустить эволюцию": {
        "уроки": [
            "🧠 Апгрейд мышления: модели гениев",
            "🚀 Экспоненциальный рост компетенций", 
            "🔧 Бесшовная интеграция AI в жизнь",
            "🌍 Позиционирование в новой реальности"
        ],
        "уровень": "🎯 Трансформация от потребителя к творцу",
        "описание": "Активируйте скрытые уровни вашего потенциала. Эволюционируйте осознанно."
    }
}

USER_PROGRESS = {}
USER_MESSAGE_IDS = {}
USER_LESSON_STATE = {}
USER_SAVED_PROGRESS = {}

# 🚀 ОБНОВЛЕННАЯ ФИНАНСОВАЯ СИСТЕМА
DEVELOPMENT_FUND = {
    "total_income": 0,
    "development_fund": 0,
    "marketing_budget": 0,
    "transactions": []
}

# 🎯 УЛУЧШЕННЫЙ ДИАЛОГОВЫЙ AI-ПРЕПОДАВАТЕЛЬ (GEMINI)
class DialogAITeacher:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.healthy = True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.healthy = False

    def _format_conversation_history(self, conversation_history):
        """Форматирует историю диалога для промпта"""
        if not conversation_history:
            return "История диалога пуста."
        
        formatted = []
        for msg in conversation_history[-6:]:  # Берем последние 6 сообщений
            role = "Студент" if msg["role"] == "student" else "Учитель"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)

    def generate_lesson_step(self, lesson_topic, user_level, conversation_history, current_step):
        if not self.healthy:
            return "🤖 Система AI временно недоступна. Пожалуйста, попробуйте позже."
        
        try:
            prompt = f"""
Ты - преподаватель NeuroTeacher, эксперт в области искусственного интеллекта и нейротехнологий.
Тема текущего урока: {lesson_topic}
Уровень студента: {user_level}
Текущий шаг в уроке: {current_step}

История диалога:
{self._format_conversation_history(conversation_history)}

Продолжи урок естественно, как опытный наставник. Будь конкретен, практичен и вдохновляющ.
Дай полезную информацию по теме, предложи практические упражнения или задай наводящий вопрос.

Формат: естественный диалог, без пометок "учитель" или "студент".
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            fallback_responses = [
                "Что вас особенно интересует в этой теме?",
                "Какой аспект готовы обсудить глубже?",
                "Есть ли конкретные вопросы по этой теме?",
                "Давайте продолжим исследовать эту тему вместе."
            ]
            return random.choice(fallback_responses)

    def create_progress_tracker(self, completed_lessons, total_lessons=4):
        progress_percent = (completed_lessons / total_lessons) * 100
        progress_bar = "🟩" * completed_lessons + "⬜" * (total_lessons - completed_lessons)
        
        achievements = []
        if completed_lessons >= 1:
            achievements.append("🎯 Начинающий")
        if completed_lessons >= 2:
            achievements.append("🚀 Практик") 
        if completed_lessons >= 4:
            achievements.append("🏆 Специалист")
            
        return {
            "progress_bar": f"{progress_bar} {progress_percent:.1f}%",
            "achievements": achievements,
            "completed": completed_lessons,
            "total": total_lessons
        }

# Инициализация преподавателя
dialog_teacher = DialogAITeacher()

def save_lesson_progress(chat_id):
    """Сохраняет текущий прогресс урока"""
    if chat_id in USER_LESSON_STATE:
        USER_SAVED_PROGRESS[chat_id] = USER_LESSON_STATE[chat_id].copy()
        logger.info(f"Прогресс сохранен для {chat_id}: {USER_SAVED_PROGRESS[chat_id]['current_lesson']}")

def restore_lesson_progress(chat_id):
    """Восстанавливает прогресс урока если есть сохраненный"""
    if chat_id in USER_SAVED_PROGRESS:
        USER_LESSON_STATE[chat_id] = USER_SAVED_PROGRESS[chat_id].copy()
        logger.info(f"Прогресс восстановлен для {chat_id}: {USER_LESSON_STATE[chat_id]['current_lesson']}")
        return True
    return False

def generate_ton_payment_link(chat_id, amount=10):
    return f"https://app.tonkeeper.com/transfer/{TON_WALLET}?amount={amount*1000000000}&text=premium_{chat_id}"

def update_user_progress(chat_id, lesson_name):
    if chat_id not in USER_PROGRESS:
        USER_PROGRESS[chat_id] = {
            "пройденные_уроки": [], 
            "уровень": 1, 
            "баллы": 0,
            "последняя_активность": datetime.now().isoformat()
        }
    
    if lesson_name not in USER_PROGRESS[chat_id]["пройденные_уроки"]:
        USER_PROGRESS[chat_id]["пройденные_уроки"].append(lesson_name)
        USER_PROGRESS[chat_id]["баллы"] += 10
        USER_PROGRESS[chat_id]["последняя_активность"] = datetime.now().isoformat()
        
        if len(USER_PROGRESS[chat_id]["пройденные_уроки"]) % 2 == 0:
            USER_PROGRESS[chat_id]["уровень"] += 1

def update_lesson_state(chat_id, lesson_name, step=0, user_message=None):
    if chat_id not in USER_LESSON_STATE:
        USER_LESSON_STATE[chat_id] = {
            "current_lesson": lesson_name,
            "step": step,
            "conversation": [],
            "started_at": datetime.now().isoformat()
        }
    
    if user_message:
        USER_LESSON_STATE[chat_id]["conversation"].append({
            "role": "student", 
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
    
    USER_LESSON_STATE[chat_id]["step"] = step
    USER_LESSON_STATE[chat_id]["last_updated"] = datetime.now().isoformat()

def add_teacher_response(chat_id, teacher_message):
    if chat_id in USER_LESSON_STATE:
        USER_LESSON_STATE[chat_id]["conversation"].append({
            "role": "teacher",
            "content": teacher_message,
            "timestamp": datetime.now().isoformat()
        })

# 🎯 ПОЛНАЯ СИСТЕМА МЕНЮ
class MenuManager:
    def get_main_menu(self):
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🚀 Войти в систему AI", "callback_data": "menu_course_🚀 Войти в систему AI"},
                    {"text": "💫 Запустить эволюцию", "callback_data": "menu_course_💫 Запустить эволюцию"}
                ],
                [
                    {"text": "💰 Премиум доступ", "callback_data": "menu_premium"},
                    {"text": "👤 Мой профиль", "callback_data": "menu_profile"}
                ],
                [
                    {"text": "🌍 Фонд развития", "callback_data": "menu_development_fund"}
                ],
                [
                    {"text": "🔄 Сбросить прогресс", "callback_data": "menu_reset"},
                    {"text": "ℹ️ Помощь", "callback_data": "menu_help"}
                ]
            ]
        }
        
        text = """🧠 *NeuroTeacher*

*Твой AI-наставник в мире нейротехнологий*

Готов прокачать твой интеллект? Выбери направление:"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_enhanced_course_menu(self, course_name, user_id):
        if course_name not in COURSES:
            return {
                "text": "❌ Курс не найден",
                "keyboard": self.get_main_menu()["keyboard"]
            }
        
        course_info = COURSES[course_name]
        progress = USER_PROGRESS.get(user_id, {"пройденные_уроки": [], "уровень": 1, "баллы": 0})
        
        progress_data = dialog_teacher.create_progress_tracker(
            len([lesson for lesson in course_info['уроки'] if lesson in progress['пройденные_уроки']])
        )
        
        lesson_buttons = []
        for i, lesson in enumerate(course_info['уроки']):
            status = "✅" if lesson in progress['пройденные_уроки'] else "📖"
            lesson_buttons.append([
                {"text": f"{status} Урок {i+1}: {lesson}", "callback_data": f"start_lesson_{course_name}_{i}"}
            ])
        
        progress_row = [{"text": f"📊 Прогресс: {progress_data['progress_bar']}", "callback_data": "show_progress"}]
        lesson_buttons.insert(0, progress_row)
        
        if progress_data['achievements']:
            achievement_row = [{"text": f"🏆 {progress_data['achievements'][-1]}", "callback_data": "show_achievements"}]
            lesson_buttons.insert(1, achievement_row)
        
        lesson_buttons.append([{"text": "🔙 Назад к меню", "callback_data": "menu_main"}])
        
        keyboard = {"inline_keyboard": lesson_buttons}
        
        text = f"""*{course_name}*

{course_info['описание']}

🤖 *Ваш прогресс:* {progress_data['completed']}/{progress_data['total']} уроков
{progress_data['progress_bar']}

💫 *Выберите урок для начала:*"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_premium_menu(self):
        payment_link = generate_ton_payment_link("premium_user")
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "💳 Активировать полный доступ", "url": payment_link}],
                [{"text": "🔙 Назад к меню", "callback_data": "menu_main"}]
            ]
        }
        
        text = """💰 *ПРЕМИУМ ДОСТУП*

Откройте полный потенциал NeuroTeacher:

✅ Все курсы и уроки
🎓 Персональный AI-наставник 24/7
📊 Детальная аналитика прогресса
🔮 Эксклюзивные материалы

⚡ *Инвестиция в развитие: 10 TON/месяц*"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_profile_menu(self, chat_id):
        progress = USER_PROGRESS.get(chat_id, {"пройденные_уроки": [], "уровень": 1, "баллы": 0})
        
        total_lessons = sum(len(course['уроки']) for course in COURSES.values())
        completed_lessons = len(progress['пройденные_уроки'])
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Сбросить прогресс", "callback_data": "reset_progress"}],
                [{"text": "🔙 Назад к меню", "callback_data": "menu_main"}]
            ]
        }
        
        text = f"""👤 *ВАШ ПРОФИЛЬ*

📊 Уровень: {progress['уровень']}
🎯 Баллы: {progress['баллы']}
📚 Пройдено уроков: {completed_lessons}/{total_lessons}

🌍 *ФОНД РАЗВИТИЯ*
💫 Собрано в фонд: {DEVELOPMENT_FUND['development_fund']} TON
🚀 Всего доходов: {DEVELOPMENT_FUND['total_income']} TON

💫 *Продолжаем обучение!*"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_development_fund_menu(self):
        keyboard = {
            "inline_keyboard": [
                [{"text": "💎 Внести вклад", "url": generate_ton_payment_link("development_fund")}],
                [{"text": "🔙 Назад к меню", "callback_data": "menu_main"}]
            ]
        }
        
        text = f"""🌍 *СИСТЕМА DEVELOPMENT FUND*

💰 Всего доходов: {DEVELOPMENT_FUND['total_income']} TON
💫 Накоплено в фонд развития: {DEVELOPMENT_FUND['development_fund']} TON  
🚀 Маркетинг бюджет: {DEVELOPMENT_FUND['marketing_budget']} TON

📊 Распределение доходов:
• 70% - развитие платформы
• 20% - маркетинг и привлечение  
• 10% - основателю

⚡ *Создаем будущее образования вместе*"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_help_menu(self):
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔙 Назад к меню", "callback_data": "menu_main"}]
            ]
        }
        
        text = """ℹ️ *ПОМОЩЬ*

*Как пользоваться NeuroTeacher:*

1. 🚀 Выберите курс из главного меню
2. 📚 Начните урок - общайтесь с AI-преподавателем
3. 💬 Отвечайте на вопросы, задавайте свои
4. 📊 Следите за прогрессом в профиле

*Команды:*
/start - Главное меню
/menu - Вернуться в меню

*Особенности:*
• Сообщения в уроках автоматически удаляются для чистоты диалога
• Прогресс сохраняется автоматически
• Можно продолжить с того же места после перерыва

*Поддержка:* @neuroteacher_support"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_dialog_lesson(self, chat_id, lesson_topic, user_input=None):
        user_level = USER_PROGRESS.get(chat_id, {}).get('уровень', 1)
        lesson_state = USER_LESSON_STATE.get(chat_id, {})
        
        conversation_history = lesson_state.get("conversation", [])
        current_step = lesson_state.get("step", 0)
        
        # Генерируем следующий шаг урока через Gemini
        teacher_response = dialog_teacher.generate_lesson_step(
            lesson_topic, 
            user_level, 
            conversation_history, 
            current_step
        )
        
        # Добавляем ответ учителя в историю
        add_teacher_response(chat_id, teacher_response)
        
        # Обновляем шаг
        update_lesson_state(chat_id, lesson_topic, current_step + 1)
        
        # Клавиатура с дополнительными опциями
        keyboard = {
            "inline_keyboard": [
                [{"text": "❓ Задать вопрос", "callback_data": "ask_question"}],
                [{"text": "📚 Следующий раздел", "callback_data": "next_section"}],
                [{"text": "🔙 Назад к курсу", "callback_data": "menu_course_back"}]
            ]
        }
        
        text = f"""📚 *{lesson_topic}*

{teacher_response}"""
        
        return {"text": text, "keyboard": keyboard}

# Инициализация менеджера
menu_manager = MenuManager()

@app.route('/')
def home():
    return jsonify({
        "status": "NeuroTeacher - Dialog Education Platform",
        "version": "4.5", 
        "ready": True,
        "ai_provider": "Gemini Flash 2.0",
        "founder_wallet": TON_WALLET,
        "users_count": len(USER_PROGRESS),
        "active_lessons": len(USER_LESSON_STATE)
    })

@app.route('/health')
def health():
    ai_status = "healthy" if dialog_teacher.healthy else "unhealthy"
    return jsonify({
        "status": "healthy", 
        "service": "NeuroTeacher", 
        "ai": ai_status,
        "users": len(USER_PROGRESS),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/stats')
def stats():
    """Статистика платформы"""
    total_lessons = sum(len(course['уроки']) for course in COURSES.values())
    completed_lessons = sum(len(user['пройденные_уроки']) for user in USER_PROGRESS.values())
    
    return jsonify({
        "total_users": len(USER_PROGRESS),
        "active_lessons": len(USER_LESSON_STATE),
        "total_completed_lessons": completed_lessons,
        "available_courses": len(COURSES),
        "available_lessons": total_lessons,
        "development_fund": DEVELOPMENT_FUND
    })

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        
        if 'callback_query' in data:
            return handle_callback_query(data['callback_query'])
        elif 'message' in data:
            return handle_message(data['message'])
        else:
            return jsonify({"status": "ignored", "message": "Unknown message type"})
            
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)})

def handle_callback_query(callback_query):
    """Обрабатывает callback запросы"""
    chat_id = callback_query['message']['chat']['id']
    callback_data = callback_query['data']
    message_id = callback_query['message']['message_id']
    
    # Ответим на callback query чтобы убрать "часики"
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
        json={"callback_query_id": callback_query['id']}
    )
    
    # ОСНОВНЫЕ ОБРАБОТЧИКИ МЕНЮ
    if callback_data == "menu_main":
        if chat_id in USER_LESSON_STATE:
            save_lesson_progress(chat_id)
        menu_data = menu_manager.get_main_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data == "menu_premium":
        menu_data = menu_manager.get_premium_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data == "menu_profile":
        menu_data = menu_manager.get_profile_menu(chat_id)
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data == "menu_development_fund":
        menu_data = menu_manager.get_development_fund_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data == "menu_help":
        menu_data = menu_manager.get_help_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data == "reset_progress":
        if chat_id in USER_PROGRESS:
            del USER_PROGRESS[chat_id]
        if chat_id in USER_LESSON_STATE:
            del USER_LESSON_STATE[chat_id]
        if chat_id in USER_SAVED_PROGRESS:
            del USER_SAVED_PROGRESS[chat_id]
        
        menu_data = menu_manager.get_main_menu()
        edit_main_message(chat_id, "✅ Прогресс сброшен! Начните заново.", menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
    elif callback_data.startswith("menu_course_"):
        course_name = callback_data.replace("menu_course_", "")
        try:
            menu_data = menu_manager.get_enhanced_course_menu(course_name, chat_id)
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        except Exception as e:
            logging.error(f"Error opening course {course_name}: {e}")
            menu_data = menu_manager.get_main_menu()
            edit_main_message(chat_id, "❌ Ошибка загрузки курса", menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
    
    # ДИАЛОГОВЫЕ УРОКИ
    elif callback_data.startswith('start_lesson_'):
        parts = callback_data.replace('start_lesson_', '').split('_')
        if len(parts) >= 2:
            course_name = parts[0]
            lesson_index = int(parts[1])
            
            if course_name in COURSES and 0 <= lesson_index < len(COURSES[course_name]['уроки']):
                lesson = COURSES[course_name]['уроки'][lesson_index]
                start_lesson_dialog(chat_id, lesson)
    
    elif callback_data == "menu_course_back":
        if chat_id in USER_LESSON_STATE:
            save_lesson_progress(chat_id)
        
        current_lesson = USER_LESSON_STATE.get(chat_id, {}).get('current_lesson', '')
        found_course = None
        
        for course_name, course_info in COURSES.items():
            if current_lesson in course_info['уроки']:
                found_course = course_name
                break
        
        if found_course:
            menu_data = menu_manager.get_enhanced_course_menu(found_course, chat_id)
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        else:
            menu_data = menu_manager.get_main_menu()
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
    
    elif callback_data == "ask_question":
        # Просто продолжаем диалог - пользователь может задать вопрос текстом
        lesson_state = USER_LESSON_STATE.get(chat_id, {})
        if lesson_state:
            current_lesson = lesson_state["current_lesson"]
            menu_data = menu_manager.get_dialog_lesson(chat_id, current_lesson, "У меня есть вопрос")
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
    
    elif callback_data == "next_section":
        lesson_state = USER_LESSON_STATE.get(chat_id, {})
        if lesson_state:
            current_lesson = lesson_state["current_lesson"]
            menu_data = menu_manager.get_dialog_lesson(chat_id, current_lesson, "Перейдите к следующему разделу")
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
    
    else:
        # Неизвестный callback - возвращаем в главное меню
        menu_data = menu_manager.get_main_menu()
        edit_main_message(chat_id, "🔄 Обновлено", menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
    
    return jsonify({"status": "ok"})

def start_lesson_dialog(chat_id, lesson):
    """Начинает диалоговый урок"""
    has_saved_progress = restore_lesson_progress(chat_id)
    
    if has_saved_progress and USER_LESSON_STATE[chat_id]['current_lesson'] == lesson:
        last_conversation = USER_LESSON_STATE[chat_id]['conversation']
        teacher_messages = [msg for msg in last_conversation if msg["role"] == "teacher"]
        
        if teacher_messages:
            last_teacher_msg = teacher_messages[-1]['content']
            summary = last_teacher_msg[:50] + "..." if len(last_teacher_msg) > 50 else last_teacher_msg
        else:
            summary = "начале урока"
        
        reactions = [
            f"Отлично, что вернулись! 😊 Продолжим с: *{summary}*",
            f"С возвращением! Мы остановились на: *{summary}*",
            f"Рад вас снова видеть! Продолжаем: *{summary}*"
        ]
        
        welcome_text = f"""🧠 *Учитель NeuroTeacher*

📚 Тема: {lesson}

{random.choice(reactions)}"""
    else:
        USER_LESSON_STATE[chat_id] = {
            "current_lesson": lesson,
            "step": 0,
            "conversation": [],
            "started_at": datetime.now().isoformat()
        }
        
        greetings = [
            f"Привет! Начнем изучать {lesson}",
            f"Добро пожаловать на урок: {lesson}",
            f"Начнем наше погружение в {lesson}"
        ]
        
        welcome_text = f"""🧠 *Учитель NeuroTeacher*

📚 Тема: {lesson}

{random.choice(greetings)}"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "❓ Задать вопрос", "callback_data": "ask_question"}],
            [{"text": "📚 Следующий раздел", "callback_data": "next_section"}],
            [{"text": "🔙 Назад к курсу", "callback_data": "menu_course_back"}]
        ]
    }
    
    edit_main_message(chat_id, welcome_text, keyboard, USER_MESSAGE_IDS.get(chat_id))

def handle_message(message):
    """Обрабатывает текстовые сообщения"""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    message_id = message.get('message_id')
    
    if not chat_id:
        return jsonify({"status": "error", "message": "No chat_id"})
    
    if text == '/start':
        menu_data = menu_manager.get_main_menu()
        send_telegram_message(chat_id, menu_data['text'], menu_data['keyboard'])
        return jsonify({"status": "ok"})
    
    elif text == '/menu':
        menu_data = menu_manager.get_main_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        return jsonify({"status": "ok"})
    
    elif text == '/stats':
        stats_text = f"""📊 *Статистика NeuroTeacher*

👥 Пользователей: {len(USER_PROGRESS)}
📚 Активных уроков: {len(USER_LESSON_STATE)}
💫 AI статус: {'✅ Работает' if dialog_teacher.healthy else '❌ Ошибка'}

💎 Фонд развития: {DEVELOPMENT_FUND['development_fund']} TON"""
        send_telegram_message(chat_id, stats_text)
        return jsonify({"status": "ok"})
    
    elif text == '/help':
        menu_data = menu_manager.get_help_menu()
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        return jsonify({"status": "ok"})
    
    # Обработка диалога в уроке
    lesson_state = USER_LESSON_STATE.get(chat_id, {})
    if lesson_state and "current_lesson" in lesson_state:
        current_lesson = lesson_state["current_lesson"]
        
        # Удаляем сообщение пользователя для чистоты диалога
        if message_id:
            delete_user_message(chat_id, message_id)
        
        # Обновляем состояние и получаем ответ
        update_lesson_state(chat_id, current_lesson, lesson_state["step"], text)
        menu_data = menu_manager.get_dialog_lesson(chat_id, current_lesson, text)
        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
        
        # Отмечаем урок как пройденный если было достаточно шагов
        if lesson_state["step"] >= 3:  # После 3 шагов считаем урок пройденным
            update_user_progress(chat_id, current_lesson)
        
        return jsonify({"status": "ok"})
    
    # Если не в уроке, показываем главное меню
    menu_data = menu_manager.get_main_menu()
    send_telegram_message(chat_id, "Выберите действие:", menu_data['keyboard'])
    return jsonify({"status": "ok"})

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Устанавливает webhook для Telegram"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        return jsonify({"status": "error", "message": "WEBHOOK_URL not set"})
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": f"{webhook_url}/webhook"}
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting NeuroTeacher bot on port {port}")
    logger.info(f"AI Teacher status: {'Healthy' if dialog_teacher.healthy else 'Unhealthy'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
