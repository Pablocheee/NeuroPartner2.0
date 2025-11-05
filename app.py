import httpx
from flask import Flask, request, jsonify
import google.generativeai as genai
import os
import requests
import logging

app = Flask(__name__)

# Настройка API ключей для Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TON_WALLET = os.getenv('TON_WALLET', 'UQAVTMHfwYcMn7ttJNXiJVaoA-jjRTeJHc2sjpkAVzc84oSY')

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

# 🚀 ОБНОВЛЕННАЯ ФИНАНСОВАЯ СИСТЕМА
DEVELOPMENT_FUND = {
    "total_income": 0,
    "development_fund": 0,
    "marketing_budget": 0,
    "transactions": []
}

def process_development_fund(amount, from_user):
    DEVELOPMENT_FUND["total_income"] += amount
    
    distribution = {
        "development": amount * 0.7,
        "marketing": amount * 0.2,
        "founder": amount * 0.1
    }
    
    DEVELOPMENT_FUND["development_fund"] += distribution["development"]
    DEVELOPMENT_FUND["marketing_budget"] += distribution["marketing"]
    DEVELOPMENT_FUND["transactions"].append({
        "amount": amount,
        "from": from_user,
        "distribution": distribution,
        "timestamp": "2025-01-11"
    })
    
    return distribution

# 🎯 УЛУЧШЕННЫЙ ДИАЛОГОВЫЙ AI-ПРЕПОДАВАТЕЛЬ (GEMINI)
class DialogAITeacher:
    def __init__(self):
        self.teacher_styles = {
            "объяснение": "🧠",
            "вопрос": "❓", 
            "практика": "🔧",
            "обратная связь": "💫"
        }
        # Настройка модели Gemini
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def generate_lesson_step(self, lesson_topic, user_level, conversation_history, current_step):
        """Генерирует следующий шаг урока используя Gemini"""
        
        system_prompt = f"""
        Ты - опытный AI-преподаватель NeuroTeacher. Веди естественный диалог с учеником.
        
        Тема урока: {lesson_topic}
        Уровень ученика: {user_level}/5
        
        История диалога:
        {self._format_conversation_history(conversation_history)}
        
        Важные правила:
        1. Будь естественным и вовлекающим
        2. Адаптируй объяснения под уровень понимания
        3. Задавай открытые вопросы
        4. Будь немного креативным в подаче
        5. Не будь слишком формальным
        6. Отвечай на русском языке
        7. Будь кратким, но информативным (максимум 3-4 предложения)
        
        Продолжи урок естественным образом:
        """
        
        try:
            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0.8
                )
            )
            return response.text
        except Exception as e:
            logging.error(f"Gemini API error: {e}")
            return "🧠 Давайте продолжим наш урок! Расскажите, что вам было наиболее интересно в предыдущей части?"

    def _format_conversation_history(self, history):
        if not history:
            return "Диалог только начинается"
        
        formatted = []
        for msg in history[-4:]:  # Берем последние 4 сообщения
            role = "Ученик" if msg["role"] == "student" else "Учитель"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)

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

def generate_ton_payment_link(chat_id, amount=10):
    return f"https://app.tonkeeper.com/transfer/UQAVTMHfwYcMn7ttJNXiJVaoA-jjRTeJHc2sjpkAVzc84oSY?amount={amount*1000000000}&text=premium_{chat_id}"

def update_user_progress(chat_id, lesson_name):
    if chat_id not in USER_PROGRESS:
        USER_PROGRESS[chat_id] = {"пройденные_уроки": [], "уровень": 1, "баллы": 0}
    
    if lesson_name not in USER_PROGRESS[chat_id]["пройденные_уроки"]:
        USER_PROGRESS[chat_id]["пройденные_уроки"].append(lesson_name)
        USER_PROGRESS[chat_id]["баллы"] += 10
        
        if len(USER_PROGRESS[chat_id]["пройденные_уроки"]) % 2 == 0:
            USER_PROGRESS[chat_id]["уровень"] += 1

def update_lesson_state(chat_id, lesson_name, step=0, user_message=None):
    if chat_id not in USER_LESSON_STATE:
        USER_LESSON_STATE[chat_id] = {
            "current_lesson": lesson_name,
            "step": step,
            "conversation": []
        }
    
    if user_message:
        USER_LESSON_STATE[chat_id]["conversation"].append({
            "role": "student", 
            "content": user_message
        })
    
    USER_LESSON_STATE[chat_id]["step"] = step

def add_teacher_response(chat_id, teacher_message):
    if chat_id in USER_LESSON_STATE:
        USER_LESSON_STATE[chat_id]["conversation"].append({
            "role": "teacher",
            "content": teacher_message
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
                ]
            ]
        }
        
        text = """🧠 *NeuroTeacher*

*Твой AI-наставник в мире нейротехнологий*

Готов прокачать твой интеллект? Выбери направление:"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_enhanced_course_menu(self, course_name, user_id):
        course_info = COURSES[course_name]
        progress = USER_PROGRESS.get(user_id, {"пройденные_уроки": [], "уровень": 1, "баллы": 0})
        
        progress_data = dialog_teacher.create_progress_tracker(
            len(progress['пройденные_уроки'])
        )
        
        lesson_buttons = []
        for i, lesson in enumerate(course_info['уроки']):
            status = "✅" if lesson in progress['пройденные_уроки'] else "📖"
            lesson_buttons.append([
                {"text": f"{status} Урок {i+1}: {lesson}", "callback_data": f"start_lesson_{hash(lesson)}"}
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
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔙 Назад к меню", "callback_data": "menu_main"}]
            ]
        }
        
        text = f"""👤 *ВАШ ПРОФИЛЬ*

📊 Уровень: {progress['уровень']}
🎯 Баллы: {progress['баллы']}
📚 Пройдено уроков: {len(progress['пройденные_уроки'])}

🌍 *ФОНД РАЗВИТИЯ*
💫 Собрано в фонд: {DEVELOPMENT_FUND['development_fund']} TON
🚀 Всего доходов: {DEVELOPMENT_FUND['total_income']} TON

💫 *Продолжаем обучение!*"""
        
        return {"text": text, "keyboard": keyboard}
    
    def get_development_fund_menu(self):
        keyboard = {
            "inline_keyboard": [
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
        
        # КЛАВИАТУРА С БОЛЬШЕ ВАРИАНТАМИ
        keyboard_buttons = []
        
        # Быстрые ответы если нужно
        if "?" in teacher_response:
            keyboard_buttons.append([{"text": "💡 Давай пример", "callback_data": "request_example"}])
            keyboard_buttons.append([{"text": "🤔 Объясни подробнее", "callback_data": "explain_more"}])
        
        keyboard_buttons.extend([
            [{"text": "✅ Завершить урок", "callback_data": f"complete_lesson_{hash(lesson_topic)}"}],
            [{"text": "🔄 Начать заново", "callback_data": f"restart_lesson_{hash(lesson_topic)}"}],
            [{"text": "🔙 Назад к курсу", "callback_data": "menu_course_back"}]
        ])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        
        # ФОРМАТИРУЕМ ТЕКСТ БЕЗ ДУБЛИРОВАНИЯ
        text = f"""📚 *{lesson_topic}*

{teacher_response}"""
        
        return {"text": text, "keyboard": keyboard}

# Инициализация менеджера
menu_manager = MenuManager()

def edit_main_message(chat_id, text, keyboard, message_id=None):
    if message_id and chat_id in USER_MESSAGE_IDS:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "reply_markup": keyboard,
                    "parse_mode": "Markdown"
                }
            )
            return response.json()
        except Exception as e:
            logging.error(f"Error editing message: {e}")
    
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
            "parse_mode": "Markdown"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        USER_MESSAGE_IDS[chat_id] = result['result']['message_id']
    
    return response.json()

@app.route('/')
def home():
    return jsonify({
        "status": "NeuroTeacher - Dialog Education Platform",
        "version": "4.4", 
        "ready": True,
        "ai_provider": "Gemini Flash 2.0",
        "founder_wallet": TON_WALLET
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "NeuroTeacher", "ai": "Gemini Flash 2.0"})

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        
        if 'callback_query' in data:
            callback_data = data['callback_query']
            chat_id = callback_data['message']['chat']['id']
            callback_text = callback_data['data']
            message_id = callback_data['message']['message_id']
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": callback_data['id']}
            )
            
            # ОСНОВНЫЕ ОБРАБОТЧИКИ МЕНЮ
            if callback_text == "menu_main":
                menu_data = menu_manager.get_main_menu()
                edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                return jsonify({"status": "ok"})
            
            elif callback_text.startswith("menu_course_"):
                course_name = callback_text.replace("menu_course_", "")
                menu_data = menu_manager.get_enhanced_course_menu(course_name, chat_id)
                edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                return jsonify({"status": "ok"})
            
            elif callback_text == "menu_premium":
                menu_data = menu_manager.get_premium_menu()
                edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                return jsonify({"status": "ok"})
            
            elif callback_text == "menu_profile":
                menu_data = menu_manager.get_profile_menu(chat_id)
                edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                return jsonify({"status": "ok"})
            
            elif callback_text == "menu_development_fund":
                menu_data = menu_manager.get_development_fund_menu()
                edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                return jsonify({"status": "ok"})
            
            # ДИАЛОГОВЫЕ УРОКИ
            elif callback_text.startswith('start_lesson_'):
                lesson_hash = callback_text.replace('start_lesson_', '')
                
                for course_name, course_info in COURSES.items():
                    for lesson in course_info['уроки']:
                        if hash(lesson) == int(lesson_hash):
                            # НАЧИНАЕМ С ЧИСТОГО СОСТОЯНИЯ
                            USER_LESSON_STATE[chat_id] = {
                                "current_lesson": lesson,
                                "step": 0,
                                "conversation": []
                            }
                            menu_data = menu_manager.get_dialog_lesson(chat_id, lesson)
                            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                            break
                return jsonify({"status": "ok"})
            
            elif callback_text.startswith('complete_lesson_'):
                lesson_hash = callback_text.replace('complete_lesson_', '')
                
                for course_name, course_info in COURSES.items():
                    for lesson in course_info['уроки']:
                        if hash(lesson) == int(lesson_hash):
                            update_user_progress(chat_id, lesson)
                            if chat_id in USER_LESSON_STATE:
                                del USER_LESSON_STATE[chat_id]
                            
                            menu_data = menu_manager.get_enhanced_course_menu(course_name, chat_id)
                            success_text = f"""🎉 *Урок завершен!*

📚 Тема: {lesson}
🎯 Получено: 10 баллов
💫 Уровень повышен!

{menu_data['text']}"""
                            
                            edit_main_message(chat_id, success_text, menu_data['keyboard'], message_id)
                            break
                return jsonify({"status": "ok"})
            
            elif callback_text.startswith('restart_lesson_'):
                lesson_hash = callback_text.replace('restart_lesson_', '')
                
                for course_name, course_info in COURSES.items():
                    for lesson in course_info['уроки']:
                        if hash(lesson) == int(lesson_hash):
                            # ПЕРЕЗАПУСКАЕМ УРОК
                            USER_LESSON_STATE[chat_id] = {
                                "current_lesson": lesson,
                                "step": 0,
                                "conversation": []
                            }
                            menu_data = menu_manager.get_dialog_lesson(chat_id, lesson)
                            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                            break
                return jsonify({"status": "ok"})
            
            elif callback_text == "menu_course_back":
                lesson_state = USER_LESSON_STATE.get(chat_id, {})
                current_lesson = lesson_state.get("current_lesson", "")
                
                for course_name, course_info in COURSES.items():
                    if current_lesson in course_info['уроки']:
                        menu_data = menu_manager.get_enhanced_course_menu(course_name, chat_id)
                        edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], message_id)
                        break
                return jsonify({"status": "ok"})

        # ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ - БЕЗ ДУБЛИРОВАНИЯ
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')

        if not chat_id:
            return jsonify({"status": "error", "message": "No chat_id"})

        if text == '/start':
            menu_data = menu_manager.get_main_menu()
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'])
            return jsonify({"status": "ok"})
        
        lesson_state = USER_LESSON_STATE.get(chat_id, {})
        if lesson_state and "current_lesson" in lesson_state:
            current_lesson = lesson_state["current_lesson"]
            
            # ОБНОВЛЯЕМ СОСТОЯНИЕ БЕЗ ОТПРАВКИ ОТДЕЛЬНОГО СООБЩЕНИЯ
            update_lesson_state(chat_id, current_lesson, lesson_state["step"], text)
            
            # ПОЛУЧАЕМ ОТВЕТ УЧИТЕЛЯ
            menu_data = menu_manager.get_dialog_lesson(chat_id, current_lesson, text)
            edit_main_message(chat_id, menu_data['text'], menu_data['keyboard'], USER_MESSAGE_IDS.get(chat_id))
            
            return jsonify({"status": "ok"})

        return jsonify({"status": "ok"})        
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
