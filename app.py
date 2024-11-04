from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# 加载配置数据
with open('data.json', 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

class DatabaseConnection:
    def __init__(self, db_name='fortunes.db'):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

def get_five_element(birthdate):
    """根据生日计算五行属性"""
    birth_date = datetime.strptime(birthdate, '%Y-%m-%d')
    month = birth_date.month
    
    if month in [3, 4]: return "木"
    elif month in [5, 6]: return "火"
    elif month in [7, 8, 9]: return "金"
    elif month in [10, 11]: return "水"
    else: return "土"

def calculate_hexagram(birthdate, name):
    """计算卦象"""
    birth_date = datetime.strptime(birthdate, '%Y-%m-%d')
    
    # 计算卦象号码
    factors = [
        birth_date.day + birth_date.month + birth_date.year,
        list(CONFIG['five_elements'].keys()).index(get_five_element(birthdate)) + 1,
        birth_date.year % 12,
        birth_date.month,
        birth_date.day,
        len(name)
    ]
    
    hexagram_number = str((sum(factors) % 64) + 1)
    hexagram = CONFIG['hexagrams'].get(hexagram_number, {
        "name": "随机卦",
        "meaning": "运势变化无常，需要随机应变。",
        "description": "天地变化，顺应自然。",
        "image": "☯",
        "elements": ["变", "通"]
    })
    
    hexagram["five_element"] = get_five_element(birthdate)
    return hexagram

def get_constellation(month, day):
    """获取星座"""
    month_day = (month, day)
    for m, d, constellation in CONFIG['constellations']:
        if month_day <= (m, d):
            return constellation
    return '摩羯座'

def init_db():
    """初始化数据库"""
    with DatabaseConnection() as conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS fortunes')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS fortunes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category TEXT NOT NULL,
                lucky_number INTEGER,
                lucky_color TEXT,
                five_element TEXT,
                season TEXT
            )
        ''')
        
        c.executemany('''
            INSERT OR IGNORE INTO fortunes 
            (text, category, lucky_number, lucky_color, five_element, season) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', CONFIG['fortunes_data'])
        conn.commit()

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/api/fortune', methods=['GET'])
def get_fortune():
    name = request.args.get('name', '张璐')
    category = request.args.get('category', '总运')
    birthdate = request.args.get('birthdate', '1981-12-27')
    
    try:
        birth_date = datetime.strptime(birthdate, '%Y-%m-%d')
        zodiac = CONFIG['zodiac_signs'][(birth_date.year - 1900) % 12]
        constellation = get_constellation(birth_date.month, birth_date.day)
        five_element = get_five_element(birthdate)
        hexagram = calculate_hexagram(birthdate, name)
        
        with DatabaseConnection() as conn:
            c = conn.cursor()
            if category == '总运':
                c.execute('SELECT * FROM fortunes WHERE five_element = ? ORDER BY RANDOM() LIMIT 1', 
                         (five_element,))
            else:
                c.execute('SELECT * FROM fortunes WHERE category = ? AND five_element = ? ORDER BY RANDOM() LIMIT 1', 
                         (category, five_element))
            
            result = c.fetchone()
            
        if result:
            return jsonify({
                'fortune': f'{name}，{result["text"]}',
                'category': result["category"],
                'lucky_number': result["lucky_number"],
                'lucky_color': result["lucky_color"],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'zodiac': zodiac,
                'constellation': constellation,
                'birthdate': birthdate,
                'five_element': five_element,
                'season': result["season"],
                'hexagram': hexagram
            })
        
        return jsonify({
            'fortune': f'{name}，今天运势平稳，宜静观其变。',
            'category': category,
            'lucky_number': 8,
            'lucky_color': '白色',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'zodiac': zodiac,
            'constellation': constellation,
            'birthdate': birthdate,
            'five_element': five_element,
            'season': '四季',
            'hexagram': hexagram
        })
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': '获取运势信息失败'
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=8080)