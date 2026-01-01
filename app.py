from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
from groq import Groq
import os
from PIL import Image, ImageFilter
import io
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Groq API anahtarı
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
client = Groq(api_key=GROQ_API_KEY)

# Sistem promptu: Sadece Türkçe konuşan yardımcı AI
SYSTEM_PROMPT = "Sen sadece Türkçe konuşan bir yardımcı AI'sin. Tüm cevaplarını Türkçe ver. Kısa ve anlaşılır ol. Sen Atlas Design tarafından oluşturulmuş bir AI'sin. Kim olduğun sorulursa, bunu belirt."

conversation_history = []

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    # In a real app, load from database
    return User(user_id, session.get('user_name'), session.get('user_email'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login/custom', methods=['POST'])
def login_custom():
    data = request.json
    email = data.get('email')

    if not email or not email.endswith('@gmail.com'):
        return jsonify({'success': False, 'error': 'Geçerli bir Gmail adresi gerekli'}), 400

    # Extract name from email (before @)
    name = email.split('@')[0]

    user = User(id=email, name=name, email=email)
    login_user(user)
    session['user_name'] = name
    session['user_email'] = email

    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Mesaj boş olamaz'}), 400

    # Konuşma geçmişini güncelle
    conversation_history.append({"role": "user", "content": user_message})

    # Groq API'ye istek gönder
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history
            ],
            max_tokens=4096,
            temperature=0.6,
            top_p=0.95
        )
        ai_response = response.choices[0].message.content.strip()
        # Remove <think> blocks from the response
        import re
        ai_response = re.sub(r'<think>.*?</think>', '', ai_response, flags=re.DOTALL).strip()

        # AI cevabını geçmişe ekle
        conversation_history.append({"role": "assistant", "content": ai_response})

        return jsonify({'response': ai_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/save_chat', methods=['POST'])
def save_chat():
    data = request.json
    chat_id = data.get('chat_id')
    chat_content = data.get('chat_content')
    if not chat_id or not chat_content:
        return jsonify({'error': 'Chat ID ve içerik gerekli'}), 400

    try:
        with open(f'chats/{chat_id}.json', 'w', encoding='utf-8') as f:
            json.dump({'chat_id': chat_id, 'content': chat_content, 'timestamp': data.get('timestamp')}, f, ensure_ascii=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load_chats', methods=['GET'])
def load_chats():
    try:
        chats = []
        if os.path.exists('chats'):
            for file in os.listdir('chats'):
                if file.endswith('.json'):
                    with open(f'chats/{file}', 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                        chats.append(chat_data)
        return jsonify({'chats': chats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('chats'):
        os.makedirs('chats')
    app.run(debug=True)
