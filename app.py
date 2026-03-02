import os
import json
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, session
import requests, time, re
import datetime
import threading

# 配置文件路径
CONFIG_FILE = 'config.yaml'
USER_CONFIG_FILE = 'user_config.yaml'

# 加载配置文件
def load_config():
    default_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "debug": True
        },
        "environment": {
            "QL_HOST": "",
            "CLIENT_ID": "",
            "CLIENT_SECRET": "",
            "ADMIN_USERNAME": "",
            "ADMIN_PASSWORD": "",
            "SECRET_KEY": "",
            "MAX_DAILY_ACCESS": 7,
            "BACKGROUND_IMAGE_URL": "https://t.alcy.cc/ycy"
        },
        "email": {
            "enabled": False,
            "smtpServer": "",
            "smtpPort": 587,
            "smtpUser": "",
            "smtpPass": "",
            "checkTime": "08:00"
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    return default_config

# 全局配置
CONFIG = load_config()

# 加载用户配置
def load_user_config():
    default_user_config = {
        "users": {}
    }
    
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # 确保返回的配置包含users键
                if config and isinstance(config, dict):
                    if 'users' not in config:
                        config['users'] = {}
                    return config
        except Exception as e:
            print(f"加载用户配置文件失败: {e}")
    # 如果文件不存在或加载失败，返回默认配置
    return default_user_config

# 保存用户配置
def save_user_config(user_config):
    try:
        # 确保user_config不是None，并且是一个字典
        if user_config is None:
            user_config = {"users": {}}
        elif not isinstance(user_config, dict):
            user_config = {"users": {}}
        elif 'users' not in user_config:
            user_config['users'] = {}
        
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(user_config, f, allow_unicode=True, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        print(f"保存用户配置文件失败: {e}")
        return False

# 全局用户配置
USER_CONFIG = load_user_config()

# 从配置中获取环境变量
def get_env(key, default=None):
    # 优先从系统环境变量获取
    if key in os.environ:
        return os.environ[key]
    # 其次从配置文件获取
    # 直接使用原始键名查找
    env_config = CONFIG.get('environment', {})
    if key in env_config:
        return env_config[key]
    # 如果找不到，尝试使用小写键名查找
    if key.lower() in env_config:
        return env_config[key.lower()]
    return default

app = Flask(__name__, static_folder="static", template_folder="static")
app.secret_key = get_env('SECRET_KEY', 'default_secret_key_for_development')

# 管理员账号密码（可通过环境变量配置）
ADMIN_USERNAME = get_env('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = get_env('ADMIN_PASSWORD', 'admin123')

# 用于存储IP访问次数的字典
# 格式: { 'ip_address': {'count': number, 'last_reset': timestamp} }
ip_access_count = {}
# 每天最大访问次数（可通过环境变量配置）
MAX_DAILY_ACCESS = int(get_env('MAX_DAILY_ACCESS', '7'))
# 背景图URL（可通过环境变量配置）
BACKGROUND_IMAGE_URL = get_env('BACKGROUND_IMAGE_URL', 'https://t.alcy.cc/ycy')


def limit_ip_access(func):
    """装饰器：限制同一IP每天的访问次数"""
    def wrapper(*args, **kwargs):
        # 获取客户端IP地址
        ip = request.remote_addr
        current_time = datetime.datetime.now()
        
        # 检查IP是否存在于记录中
        if ip in ip_access_count:
            access_info = ip_access_count[ip]
            last_reset = datetime.datetime.fromtimestamp(access_info['last_reset'])
            
            # 检查是否需要重置计数（过了一天）
            if (current_time - last_reset).days >= 1:
                # 重置访问计数
                ip_access_count[ip] = {
                    'count': 1,
                    'last_reset': current_time.timestamp()
                }
            else:
                # 检查是否超过最大访问次数
                if access_info['count'] >= MAX_DAILY_ACCESS:
                    # 计算剩余重置时间（秒）
                    next_reset = last_reset + datetime.timedelta(days=1)
                    reset_in_seconds = (next_reset - current_time).total_seconds()
                    hours, remainder = divmod(int(reset_in_seconds), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    remaining = 0
                    return jsonify({
                        "code": 429,
                        "message": f"访问次数过多，今日剩余次数：{remaining}次，请{hours}小时{minutes}分钟{seconds}秒后再试"
                    })
                
                # 增加访问计数
                ip_access_count[ip]['count'] += 1
        else:
            # 首次访问，初始化计数
            ip_access_count[ip] = {
                'count': 1,
                'last_reset': current_time.timestamp()
            }
        
        # 执行原函数
        # 获取当前IP的剩余次数
        ip = request.remote_addr
        current_count = ip_access_count.get(ip, {}).get('count', 1)
        remaining = MAX_DAILY_ACCESS - current_count
        
        # 执行原函数并获取响应
        response = func(*args, **kwargs)
        
        # 如果是JSON响应，添加剩余次数信息
        if isinstance(response, Flask.response_class) and response.content_type == 'application/json':
            # 解析JSON内容
            data = json.loads(response.get_data(as_text=True))
            # 响应中添加剩余次数
            # if data.get('code') == 200:
            if True:
                data['remaining_times'] = remaining
                data['message'] = f"{data['message']}，今日剩余次数：{remaining}次"
                # 重新创建响应
                response.data = json.dumps(data)
        
        return response
    
    # 保留原函数的元数据
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

# 从环境变量中读取配置，如未设置则使用默认值
QL_HOST = get_env('QL_HOST', '')
CLIENT_ID = get_env('CLIENT_ID', '')
CLIENT_SECRET = get_env('CLIENT_SECRET', '')

_cached_token = None
_token_expire_time = 0

def get_ql_token():
    global _cached_token, _token_expire_time
    if _cached_token and time.time() < _token_expire_time - 60:
        return _cached_token
    url = f"{QL_HOST}/open/auth/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
    res = requests.get(url, verify=False)
    data = res.json()
    if data.get("code") != 200:
        raise Exception(f"获取Token失败: {data}")
    token = data["data"]["token"]
    _cached_token = token
    _token_expire_time = data["data"]["expiration"]
    return token

# 加载邮件配置
def load_email_config():
    # 从config.yaml中获取邮件配置
    email_config = CONFIG.get('email', {})
    if email_config:
        return email_config
    
    # 默认配置
    return {
        'smtpServer': '',
        'smtpPort': 587,
        'smtpUser': '',
        'smtpPass': '',
        'checkTime': '08:00',
        'enabled': False
    }

# 保存邮件配置
def save_email_config(config):
    try:
        # 更新config.yaml中的邮件配置
        config_data = load_config()
        config_data['email'] = config
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, indent=2)
        
        # 更新全局配置
        global CONFIG
        CONFIG = config_data
        
        return True
    except Exception as e:
        print(f"保存邮件配置失败: {e}")
        return False

# 发送邮件
def send_email(to, subject, body):
    config = load_email_config()
    if not config.get('enabled'):
        return False, "邮件提醒未启用"
    
    try:
        smtp_server = config.get('smtpServer')
        smtp_port = int(config.get('smtpPort', 587))
        smtp_user = config.get('smtpUser')
        smtp_pass = config.get('smtpPass')
        
        if not smtp_server or not smtp_port or not smtp_user or not smtp_pass:
            return False, "邮件配置不完整"
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 根据端口号选择使用SMTP还是SMTP_SSL
        if smtp_port == 465:
            # 使用SSL连接
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # 使用普通SMTP连接
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return True, "邮件发送成功"
    except Exception as e:
        return False, f"邮件发送失败: {str(e)}"

# 检查COOKIE是否到期
def check_cookies_expiry():
    try:
        config = load_email_config()
        if not config.get('enabled'):
            return
        
        # 获取所有 JD_COOKIE
        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=JD_COOKIE", headers=headers, verify=False, timeout=10)
        envs_data = res.json()
        
        if envs_data.get("code") != 200:
            return
        
        envs = envs_data.get("data", [])
        
        # 检查每个COOKIE是否到期（这里简化处理，实际需要根据COOKIE的有效期判断）
        for env in envs:
            # 从value中提取pt_pin和可能的邮箱
            value = env.get('value', '')
            pt_pin_match = re.search(r'pt_pin=([^;]+);?', value)
            if not pt_pin_match:
                continue
            
            pt_pin = pt_pin_match.group(1)
            
            # 从用户配置中获取邮箱和邮件通知设置
            user_config = {}
            if USER_CONFIG and isinstance(USER_CONFIG, dict):
                user_config = USER_CONFIG.get('users', {}).get(pt_pin, {})
            email = user_config.get('email')
            emailNotification = user_config.get('emailNotification', False)
            
            if not email or not emailNotification:
                continue
            
            # 检查COOKIE是否过期（这里简化处理，实际需要根据COOKIE的有效期判断）
            # 假设超过7天未更新的COOKIE视为过期
            updated_at = env.get('updatedAt')
            if updated_at:
                updated_time = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                current_time = datetime.datetime.now(datetime.timezone.utc)
                days_diff = (current_time - updated_time).days
                
                if days_diff >= 1:
                    # 发送邮件提醒
                    subject = "JD_COOKIE 到期提醒"
                    update_url = CONFIG.get('server', {}).get('updateUrl', 'http://localhost:8082')
                    body = f"尊敬的用户，您的 JD_COOKIE (pt_pin: {pt_pin}) 已超过7天未更新，可能已过期，请及时更新。\n\n"
                    body += f"更新链接: {update_url}\n\n"
                    body += "如需关闭提醒，请登录系统后在邮箱通知设置中关闭邮件通知。"
                    send_email(email, subject, body)
    except Exception as e:
        print(f"检查COOKIE到期失败: {e}")

# 启动邮件检查定时器
def start_email_check_timer():
    def check_timer():
        while True:
            try:
                config = load_email_config()
                check_time = config.get('checkTime', '08:00')
                hour, minute = map(int, check_time.split(':'))
                
                # 计算下次检查时间
                now = datetime.datetime.now()
                next_check = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_check <= now:
                    next_check += datetime.timedelta(days=1)
                
                # 等待到下次检查时间
                wait_seconds = (next_check - now).total_seconds()
                time.sleep(wait_seconds)
                
                # 执行检查
                check_cookies_expiry()
            except Exception as e:
                print(f"邮件检查定时器错误: {e}")
                time.sleep(3600)  # 出错后等待1小时再重试
    
    # 启动定时器线程
    timer_thread = threading.Thread(target=check_timer, daemon=True)
    timer_thread.start()

@app.route("/")
def index():
    return render_template("jdupdate.html")

# @app.route("/jdupdate")
# def jdupdate_page():
#     return render_template("jdupdate.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    """返回前端配置信息"""
    return jsonify({
        "code": 200,
        "data": {
            "backgroundImageUrl": BACKGROUND_IMAGE_URL
        }
    })

@app.route("/api/envs", methods=["GET"])
def get_envs():
    try:
        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=", headers=headers, verify=False, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/jdcookie/query", methods=["GET"])
@limit_ip_access
def query_jdcookie():
    """
    查询参数: ptpin - 要查询的 pt_pin 值
    """
    try:
        ptpin = request.args.get("ptpin")
        if not ptpin:
            return jsonify({"code": 400, "message": "ptpin 参数不能为空"})

        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 获取所有 JD_COOKIE
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=JD_COOKIE", headers=headers, verify=False, timeout=10)
        envs_data = res.json()
        if envs_data.get("code") is not 200:
            return jsonify({"code": 500, "message": "获取环境变量失败"})

        envs = envs_data.get("data", [])
        # 找到匹配 pt_pin 的 cookie
        target_env = None
        for env in envs:
            if f"pt_pin={ptpin}" in env["value"]:
                target_env = env
                break
        if not target_env:
            return jsonify({"code": 404, "message": "未找到对应 pt_pin 的 JD_COOKIE"})

        # 返回环境变量的所有状态信息
        env_info = {
            "id": target_env["id"],
            "name": target_env["name"],
            "value": target_env["value"],
            "remarks": target_env.get("remarks", ""),
            "status": target_env.get("status", 1),  # 0: 启用, 1: 禁用
            "updatedAt": target_env.get("updatedAt", "")
        }
        
        return jsonify({"code": 200, "message": "查询成功", "data": env_info})

    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/jdcookie/update", methods=["POST"])
@limit_ip_access
def update_jdcookie():
    """
    body: { "value": "完整 JD_COOKIE 值" }
    """
    try:
        data = request.json
        new_value = data.get("value")
        if not new_value:
            return jsonify({"code": 400, "message": "JD_COOKIE 值不能为空"})

        # 从 value 中提取 pt_pin
        match = re.search(r"pt_pin=([^;]+);?", new_value)
        if not match:
            return jsonify({"code": 400, "message": "JD_COOKIE 中未找到 pt_pin"})
        pt_pin = match.group(1)

        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 获取所有 JD_COOKIE
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=JD_COOKIE", headers=headers, verify=False, timeout=10)
        envs_data = res.json()
        if envs_data.get("code") is not 200:
            return jsonify({"code": 500, "message": "获取环境变量失败"})

        envs = envs_data.get("data", [])
        # 找到匹配 pt_pin 的 cookie
        target_env = None
        for env in envs:
            if f"pt_pin={pt_pin}" in env["value"]:
                target_env = env
                break
        if not target_env:
            return jsonify({"code": 404, "message": "未找到对应 pt_pin 的 JD_COOKIE"})

        env_id = target_env["id"]
        status = target_env.get("status", 1)  # 默认禁用

        if status == 0:
            return jsonify({"code": 200, "message": "环境变量已启用，无需更新"})

        # 更新 value
        payload = {
            "id": env_id,
            "name": target_env["name"],
            "value": new_value,
            "remarks": target_env.get("remarks", "")
        }
        res_update = requests.put(f"{QL_HOST}/open/envs", headers=headers, json=payload, verify=False, timeout=10)
        update_result = res_update.json()
        if update_result.get("code") is not 200:
            return jsonify({"code": 500, "message": f"更新环境变量失败: {update_result}"})

        # 启用环境变量
        enable_payload = [env_id]
        res_enable = requests.put(
            f"{QL_HOST}/open/envs/enable",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=enable_payload,
            verify=False,
            timeout=10
        )
        enable_result = res_enable.json()
        if enable_result.get("code") != 200:
            return jsonify({"code": 500, "message": f"启用环境变量失败: {enable_result}"})

        return jsonify({"code": 200, "message": "更新并启用成功"})

    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/jdcookie/bind-email", methods=["POST"])
@limit_ip_access
def bind_email():
    """
    body: { "ptpin": "pt_pin 值", "email": "邮箱地址", "emailNotification": true/false }
    """
    try:
        data = request.json
        ptpin = data.get("ptpin")
        email = data.get("email")
        emailNotification = data.get("emailNotification", False)
        
        if not ptpin or not email:
            return jsonify({"code": 400, "message": "ptpin 和邮箱地址不能为空"})
        
        # 验证邮箱格式
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({"code": 400, "message": "邮箱地址格式不正确"})
        
        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # 获取所有 JD_COOKIE
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=JD_COOKIE", headers=headers, verify=False, timeout=10)
        envs_data = res.json()
        if envs_data.get("code") is not 200:
            return jsonify({"code": 500, "message": "获取环境变量失败"})
        
        envs = envs_data.get("data", [])
        # 找到匹配 pt_pin 的 cookie
        target_env = None
        for env in envs:
            if f"pt_pin={ptpin}" in env["value"]:
                target_env = env
                break
        if not target_env:
            return jsonify({"code": 404, "message": "未找到对应 pt_pin 的 JD_COOKIE"})
        
        # 更新用户配置
        global USER_CONFIG
        # 确保USER_CONFIG不是None，并且是一个字典，包含users键
        if USER_CONFIG is None:
            USER_CONFIG = {"users": {}}
        elif not isinstance(USER_CONFIG, dict):
            USER_CONFIG = {"users": {}}
        elif 'users' not in USER_CONFIG:
            USER_CONFIG['users'] = {}
        elif not isinstance(USER_CONFIG['users'], dict):
            USER_CONFIG['users'] = {}
        
        USER_CONFIG['users'][ptpin] = {
            "email": email,
            "emailNotification": emailNotification
        }
        
        # 保存用户配置
        if not save_user_config(USER_CONFIG):
            return jsonify({"code": 500, "message": "保存用户配置失败"})
        
        # 发送测试邮件，确认邮箱绑定成功
        subject = "邮箱绑定成功通知"
        update_url = CONFIG.get('server', {}).get('updateUrl', 'http://localhost:8082')
        body = f"尊敬的用户，您的邮箱 {email} 已成功绑定到 JD_COOKIE (pt_pin: {ptpin})。\n\n"
        body += "当您的 JD_COOKIE 过期时，系统将通过此邮箱发送提醒通知。\n\n"
        body += f"更新链接: {update_url}\n\n"
        body += "如需关闭提醒，请登录系统后在邮箱通知设置中关闭邮件通知。"
        send_email(email, subject, body)
        
        return jsonify({"code": 200, "message": "邮箱绑定成功，已发送测试邮件"})
        
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

# 管理员相关路由

@app.route("/admin/login")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin")
def admin_page():
    # 检查登录状态
    if not session.get('admin_logged_in'):
        return flask.redirect("/admin/login")
    return render_template("admin.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login_api():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"code": 400, "message": "用户名和密码不能为空"})
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return jsonify({"code": 200, "message": "登录成功"})
        else:
            return jsonify({"code": 401, "message": "用户名或密码错误"})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout_api():
    try:
        session.pop('admin_logged_in', None)
        return jsonify({"code": 200, "message": "登出成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/user-config")
def get_user_config():
    """
    获取用户配置，包括邮箱和邮件通知设置
    """
    try:
        # 确保USER_CONFIG不是None，并且包含users键
        if USER_CONFIG is None:
            return jsonify({"code": 200, "data": {}})
        elif 'users' not in USER_CONFIG:
            return jsonify({"code": 200, "data": {}})
        
        return jsonify({"code": 200, "data": USER_CONFIG['users']})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/check")
def admin_check_api():
    try:
        if session.get('admin_logged_in'):
            return jsonify({"code": 200, "message": "已登录"})
        else:
            return jsonify({"code": 401, "message": "未登录"})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/cookies")
def admin_get_cookies():
    try:
        # 检查登录状态
        if not session.get('admin_logged_in'):
            return jsonify({"code": 401, "message": "未登录"})
        
        # 获取所有 JD_COOKIE
        token = get_ql_token()
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{QL_HOST}/open/envs?searchValue=JD_COOKIE", headers=headers, verify=False, timeout=10)
        envs_data = res.json()
        
        if envs_data.get("code") != 200:
            return jsonify({"code": 500, "message": "获取环境变量失败"})
        
        envs = envs_data.get("data", [])
        return jsonify({"code": 200, "message": "获取成功", "data": envs})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

# 邮件系统相关API

@app.route("/api/admin/email/config", methods=["GET"])
def get_email_config():
    try:
        # 检查登录状态
        if not session.get('admin_logged_in'):
            return jsonify({"code": 401, "message": "未登录"})
        
        config = load_email_config()
        return jsonify({"code": 200, "message": "获取成功", "data": config})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/email/config", methods=["POST"])
def save_email_config_api():
    try:
        # 检查登录状态
        if not session.get('admin_logged_in'):
            return jsonify({"code": 401, "message": "未登录"})
        
        data = request.json
        if not data:
            return jsonify({"code": 400, "message": "配置不能为空"})
        
        success = save_email_config(data)
        if success:
            return jsonify({"code": 200, "message": "保存成功"})
        else:
            return jsonify({"code": 500, "message": "保存失败"})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

@app.route("/api/admin/email/test", methods=["POST"])
def send_test_email():
    try:
        # 检查登录状态
        if not session.get('admin_logged_in'):
            return jsonify({"code": 401, "message": "未登录"})
        
        # 获取测试邮箱地址
        data = request.json
        test_email = data.get('email') if data else None
        
        # 如果没有提供测试邮箱，从配置中获取管理员邮箱
        if not test_email:
            test_email = get_env('ADMIN_EMAIL', '')
            if not test_email:
                return jsonify({"code": 400, "message": "请提供测试邮箱地址或在配置文件中设置ADMIN_EMAIL"})
        
        # 发送测试邮件
        subject = "测试邮件 - JD_COOKIE 管理系统"
        body = "这是一封测试邮件，用于验证邮件系统是否正常工作。"
        success, message = send_email(test_email, subject, body)
        if success:
            return jsonify({"code": 200, "message": "测试邮件发送成功"})
        else:
            return jsonify({"code": 500, "message": f"测试邮件发送失败: {message}"})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})

if __name__ == "__main__":
    # 启动邮件检查定时器
    start_email_check_timer()
    # 从配置中获取服务器参数
    host = CONFIG.get('server', {}).get('host', '0.0.0.0')
    port = CONFIG.get('server', {}).get('port', 8080)
    debug = CONFIG.get('server', {}).get('debug', True)
    app.run(host=host, port=port, debug=debug)
