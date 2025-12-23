"""
专家系统 Web 服务器
使用 Flask 提供 REST API，供 Vue3 前端调用
可作为独立服务器运行，也可被GUI集成调用
"""

import json
import os
import sys
import uuid
from datetime import datetime
from functools import wraps
from threading import Thread

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from Rule_reasoner import Rule_reasoner

# 确定静态文件路径
if getattr(sys, 'frozen', False):
    # 打包后的exe - 静态资源在临时解压目录 _MEIPASS
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

_static_folder = os.path.join(_base, 'web_frontend', 'dist')

app = Flask(__name__, static_folder=_static_folder, static_url_path='')
CORS(app)

# 服务器运行状态
_server_thread = None
_server_running = False

# ========== 数据存储路径（用户数据应存在exe同目录，而非临时目录）==========
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RULES_FILE = os.path.join(BASE_PATH, "rules.json")
USERS_FILE = os.path.join(BASE_PATH, "users.json")
HISTORY_FILE = os.path.join(BASE_PATH, "inference_history.json")

# ========== 默认规则 ==========
DEFAULT_RULES = [
    (["毛发"], "哺乳动物"),
    (["有奶"], "哺乳动物"),
    (["羽毛"], "鸟"),
    (["会飞", "下蛋"], "鸟"),
    (["吃肉"], "肉食动物"),
    (["犬齿", "有爪", "眼盯前方"], "肉食动物"),
    (["哺乳动物", "有蹄"], "蹄类动物"),
    (["哺乳动物", "反刍动物"], "蹄类动物"),
    (["哺乳动物", "肉食动物", "黄褐色", "暗斑点"], "金钱豹"),
    (["哺乳动物", "肉食动物", "黄褐色", "黑色条纹"], "老虎"),
    (["蹄类动物", "长脖子", "长腿", "暗斑点"], "长颈鹿"),
    (["蹄类动物", "黑色条纹"], "斑马"),
    (["鸟", "长脖子", "长腿", "黑白两色", "不飞"], "鸵鸟"),
    (["鸟", "游泳", "黑白两色", "不飞"], "企鹅"),
    (["鸟", "善飞"], "信天翁"),
]

# ========== 数据加载与保存 ==========

def load_json(filepath: str, default=None):
    """加载 JSON 文件"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def save_json(filepath: str, data):
    """保存 JSON 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_rules() -> list:
    """加载规则"""
    data = load_json(RULES_FILE, {"rules": []})
    rules = data.get("rules", [])
    if not rules:
        rules = [[list(pres), ans] for pres, ans in DEFAULT_RULES]
        save_rules(rules)
    return rules


def save_rules(rules: list):
    """保存规则"""
    save_json(RULES_FILE, {"rules": rules})


def load_users() -> dict:
    """加载用户数据"""
    data = load_json(USERS_FILE, {"users": {}, "sessions": {}})
    # 确保有默认管理员
    if "admin" not in data.get("users", {}):
        data["users"] = data.get("users", {})
        data["users"]["admin"] = {
            "password": "admin123",
            "role": "admin",
            "created_at": datetime.now().isoformat()
        }
        save_json(USERS_FILE, data)
    return data


def save_users(data: dict):
    """保存用户数据"""
    save_json(USERS_FILE, data)


def load_history() -> list:
    """加载推理历史"""
    data = load_json(HISTORY_FILE, {"history": []})
    return data.get("history", [])


def save_history(history: list):
    """保存推理历史"""
    save_json(HISTORY_FILE, {"history": history})


# ========== 会话管理 ==========
sessions = {}  # token -> {username, role, reasoner_state}


def get_session(token: str):
    """获取会话"""
    return sessions.get(token)


def require_auth(f):
    """需要认证的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = get_session(token)
        if not session:
            return jsonify({"error": "未授权访问"}), 401
        request.session = session
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """需要管理员权限的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        session = get_session(token)
        if not session:
            return jsonify({"error": "未授权访问"}), 401
        if session.get('role') != 'admin':
            return jsonify({"error": "需要管理员权限"}), 403
        request.session = session
        return f(*args, **kwargs)
    return decorated


# ========== 推理器管理 ==========
# 每个会话维护独立的推理器状态
class ReasonerSession:
    def __init__(self):
        self.reasoner = Rule_reasoner()
        self.rules = load_rules()
        self.reasoner.reset([(pres, ans) for pres, ans in self.rules])
        self.known_facts = [[], []]  # [用户事实, 推理中间事实]
        self.false_facts = []
        self.path_all = []
        self.backward_target = None
        self.backward_in_progress = False

    def reset_state(self):
        """重置推理状态"""
        self.reasoner.clear_known()
        self.reasoner.clear_false()
        self.known_facts = [[], []]
        self.false_facts = []
        self.path_all = []
        self.backward_target = None
        self.backward_in_progress = False

    def reload_rules(self):
        """重新加载规则"""
        self.rules = load_rules()
        self.reasoner.reset([(pres, ans) for pres, ans in self.rules])

    def get_all_atoms(self) -> set:
        """获取所有原子命题"""
        atoms = set()
        conclusions = set()
        for pres, ans in self.rules:
            for p in pres:
                atoms.add(p)
            conclusions.add(ans)
        return atoms - conclusions

    def get_all_conclusions(self) -> set:
        """获取所有结论"""
        return {ans for _, ans in self.rules}


def get_reasoner_session(session: dict) -> ReasonerSession:
    """获取或创建推理器会话"""
    if 'reasoner_session' not in session:
        session['reasoner_session'] = ReasonerSession()
    return session['reasoner_session']


# ========== API 路由 ==========

@app.route('/')
def index():
    """服务前端页面"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """服务静态文件"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ========== 认证 API ==========

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    users_data = load_users()
    user = users_data.get('users', {}).get(username)

    if not user or user['password'] != password:
        return jsonify({"error": "用户名或密码错误"}), 401

    token = str(uuid.uuid4())
    sessions[token] = {
        'username': username,
        'role': user['role'],
        'login_time': datetime.now().isoformat()
    }

    return jsonify({
        "token": token,
        "username": username,
        "role": user['role']
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    users_data = load_users()
    if username in users_data.get('users', {}):
        return jsonify({"error": "用户名已存在"}), 400

    users_data['users'][username] = {
        "password": password,
        "role": "user",
        "created_at": datetime.now().isoformat()
    }
    save_users(users_data)

    return jsonify({"message": "注册成功"})


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """用户登出"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token in sessions:
        del sessions[token]
    return jsonify({"message": "已登出"})


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """获取当前用户信息"""
    return jsonify({
        "username": request.session['username'],
        "role": request.session['role']
    })


# ========== 规则 API ==========

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """获取所有规则"""
    rules = load_rules()
    return jsonify({
        "rules": [{"id": i, "premises": pres, "conclusion": ans}
                  for i, (pres, ans) in enumerate(rules)]
    })


@app.route('/api/rules', methods=['POST'])
@require_admin
def add_rule():
    """添加规则（需要管理员权限）"""
    data = request.json
    premises = data.get('premises', [])
    conclusion = data.get('conclusion', '')

    if not premises or not conclusion:
        return jsonify({"error": "前提和结论不能为空"}), 400

    rules = load_rules()
    rules.append([premises, conclusion])
    save_rules(rules)

    # 刷新所有会话的规则
    for session in sessions.values():
        if 'reasoner_session' in session:
            session['reasoner_session'].reload_rules()

    return jsonify({"message": "规则添加成功", "id": len(rules) - 1})


@app.route('/api/rules/batch', methods=['POST'])
@require_admin
def batch_add_rules():
    """批量添加规则（需要管理员权限）"""
    data = request.json
    new_rules = data.get('rules', [])

    if not new_rules:
        return jsonify({"error": "规则列表不能为空"}), 400

    rules = load_rules()
    for rule in new_rules:
        premises = rule.get('premises', [])
        conclusion = rule.get('conclusion', '')
        if premises and conclusion:
            rules.append([premises, conclusion])

    save_rules(rules)

    for session in sessions.values():
        if 'reasoner_session' in session:
            session['reasoner_session'].reload_rules()

    return jsonify({"message": f"成功添加 {len(new_rules)} 条规则"})


@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@require_admin
def update_rule(rule_id):
    """更新规则（需要管理员权限）"""
    data = request.json
    premises = data.get('premises', [])
    conclusion = data.get('conclusion', '')

    if not premises or not conclusion:
        return jsonify({"error": "前提和结论不能为空"}), 400

    rules = load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        return jsonify({"error": "规则不存在"}), 404

    rules[rule_id] = [premises, conclusion]
    save_rules(rules)

    for session in sessions.values():
        if 'reasoner_session' in session:
            session['reasoner_session'].reload_rules()

    return jsonify({"message": "规则更新成功"})


@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@require_admin
def delete_rule(rule_id):
    """删除规则（需要管理员权限）"""
    rules = load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        return jsonify({"error": "规则不存在"}), 404

    rules.pop(rule_id)
    save_rules(rules)

    for session in sessions.values():
        if 'reasoner_session' in session:
            session['reasoner_session'].reload_rules()

    return jsonify({"message": "规则删除成功"})


@app.route('/api/rules/reset', methods=['POST'])
@require_admin
def reset_rules():
    """重置为默认规则（需要管理员权限）"""
    rules = [[list(pres), ans] for pres, ans in DEFAULT_RULES]
    save_rules(rules)

    for session in sessions.values():
        if 'reasoner_session' in session:
            session['reasoner_session'].reload_rules()

    return jsonify({"message": "规则已重置"})


# ========== 事实 API ==========

@app.route('/api/facts/atoms', methods=['GET'])
@require_auth
def get_atoms():
    """获取所有可用的原子命题"""
    rs = get_reasoner_session(request.session)
    return jsonify({"atoms": sorted(list(rs.get_all_atoms()))})


@app.route('/api/facts/conclusions', methods=['GET'])
@require_auth
def get_conclusions():
    """获取所有可能的结论"""
    rs = get_reasoner_session(request.session)
    return jsonify({"conclusions": sorted(list(rs.get_all_conclusions()))})


@app.route('/api/facts/known', methods=['GET'])
@require_auth
def get_known_facts():
    """获取当前已知事实"""
    rs = get_reasoner_session(request.session)
    return jsonify({
        "user_facts": rs.known_facts[0],
        "derived_facts": rs.known_facts[1]
    })


@app.route('/api/facts/known', methods=['POST'])
@require_auth
def set_known_facts():
    """设置已知事实"""
    data = request.json
    facts = data.get('facts', [])

    rs = get_reasoner_session(request.session)

    # 如果移除了事实，需要重置状态
    old_facts = set(rs.known_facts[0])
    new_facts = set(facts)
    if old_facts - new_facts:
        rs.path_all = []
        rs.known_facts[1] = []
        rs.backward_in_progress = False

    rs.known_facts[0] = facts
    rs.reasoner.clear_known()
    rs.reasoner.add_known(facts)

    return jsonify({"message": "事实已更新"})


@app.route('/api/facts/false', methods=['GET'])
@require_auth
def get_false_facts():
    """获取已知为假的事实"""
    rs = get_reasoner_session(request.session)
    return jsonify({"facts": rs.false_facts})


@app.route('/api/facts/false', methods=['POST'])
@require_auth
def set_false_facts():
    """设置已知为假的事实"""
    data = request.json
    facts = data.get('facts', [])

    rs = get_reasoner_session(request.session)
    rs.false_facts = facts
    rs.reasoner.clear_false()
    rs.reasoner.add_false(facts)

    return jsonify({"message": "事实已更新"})


@app.route('/api/facts/clear', methods=['POST'])
@require_auth
def clear_facts():
    """清空所有事实"""
    rs = get_reasoner_session(request.session)
    rs.reset_state()
    return jsonify({"message": "事实已清空"})


# ========== 推理 API ==========

@app.route('/api/inference/forward', methods=['POST'])
@require_auth
def forward_inference():
    """正向推理"""
    rs = get_reasoner_session(request.session)

    if not rs.known_facts[0]:
        return jsonify({"error": "请先添加已知事实"}), 400

    conclusions, path = rs.reasoner.find()

    # 更新路径
    rs.path_all += [r for r in path if r not in rs.path_all]

    # 更新推导出的事实
    for rule_id in path:
        if rule_id < len(rs.rules):
            derived = rs.rules[rule_id][1]
            if derived not in rs.known_facts[1]:
                rs.known_facts[1].append(derived)

    result = {
        "conclusions": conclusions,
        "path": rs.path_all,
        "rules": [{"id": i, "premises": pres, "conclusion": ans}
                  for i, (pres, ans) in enumerate(rs.rules)],
        "known_facts": rs.known_facts[0],
        "derived_facts": rs.known_facts[1]
    }

    # 保存历史
    if conclusions:
        save_inference_history(
            request.session['username'],
            "forward",
            rs.known_facts[0],
            conclusions[0] if conclusions else "",
            rs.path_all
        )

    return jsonify(result)


@app.route('/api/inference/backward/start', methods=['POST'])
@require_auth
def start_backward():
    """开始反向推理"""
    data = request.json
    target = data.get('target', '')

    if not target:
        return jsonify({"error": "请指定目标结论"}), 400

    rs = get_reasoner_session(request.session)
    rs.backward_target = target
    rs.backward_in_progress = True

    return continue_backward_internal(rs, request.session)


@app.route('/api/inference/backward/continue', methods=['POST'])
@require_auth
def continue_backward():
    """继续反向推理（提供查询的事实回答）"""
    data = request.json
    true_facts = data.get('true_facts', [])
    false_facts = data.get('false_facts', [])

    rs = get_reasoner_session(request.session)

    if not rs.backward_in_progress:
        return jsonify({"error": "没有进行中的反向推理"}), 400

    # 添加事实
    if true_facts:
        rs.reasoner.add_known(true_facts)
        rs.known_facts[0].extend(true_facts)

    if false_facts:
        rs.reasoner.add_false(false_facts)
        rs.false_facts.extend(false_facts)

    return continue_backward_internal(rs, request.session)


def continue_backward_internal(rs: ReasonerSession, session: dict):
    """内部执行反向推理步骤"""
    status, data, path = rs.reasoner.step_backward(rs.backward_target)

    # 更新路径
    rs.path_all += [r for r in path if r not in rs.path_all]

    # 更新推导出的事实
    for rule_id in path:
        if rule_id < len(rs.rules):
            derived = rs.rules[rule_id][1]
            if derived not in rs.known_facts[1]:
                rs.known_facts[1].append(derived)

    result = {
        "path": rs.path_all,
        "rules": [{"id": i, "premises": pres, "conclusion": ans}
                  for i, (pres, ans) in enumerate(rs.rules)],
        "known_facts": rs.known_facts[0],
        "derived_facts": rs.known_facts[1],
        "target": rs.backward_target
    }

    if status == 0:  # 成功
        rs.backward_in_progress = False
        result["status"] = "success"
        result["message"] = f"目标 '{rs.backward_target}' 已证明成立"

        save_inference_history(
            session['username'],
            "backward",
            rs.known_facts[0],
            rs.backward_target,
            rs.path_all
        )

    elif status == 1:  # 失败
        rs.backward_in_progress = False
        result["status"] = "failed"
        result["message"] = f"无法证明目标 '{rs.backward_target}' 成立"

    elif status == 2:  # 需要询问
        result["status"] = "query"
        result["query_facts"] = [f for f in data if f not in rs.known_facts[0]]
        result["message"] = "需要确认以下事实"

    return jsonify(result)


def save_inference_history(username: str, inference_type: str,
                           facts: list, conclusion: str, path: list):
    """保存推理历史"""
    history = load_history()
    history.append({
        "id": str(uuid.uuid4()),
        "username": username,
        "type": inference_type,
        "facts": facts,
        "conclusion": conclusion,
        "path": path,
        "timestamp": datetime.now().isoformat()
    })
    # 只保留最近1000条
    if len(history) > 1000:
        history = history[-1000:]
    save_history(history)


# ========== 历史记录 API ==========

@app.route('/api/history', methods=['GET'])
@require_auth
def get_history():
    """获取推理历史"""
    history = load_history()
    username = request.session['username']
    role = request.session['role']

    # 管理员可以看到所有历史，普通用户只能看自己的
    if role != 'admin':
        history = [h for h in history if h.get('username') == username]

    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    total = len(history)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        "history": list(reversed(history[start:end])),
        "total": total,
        "page": page,
        "per_page": per_page
    })


@app.route('/api/history/<history_id>', methods=['DELETE'])
@require_auth
def delete_history(history_id):
    """删除历史记录"""
    history = load_history()
    username = request.session['username']
    role = request.session['role']

    new_history = []
    deleted = False
    for h in history:
        if h.get('id') == history_id:
            if role == 'admin' or h.get('username') == username:
                deleted = True
                continue
        new_history.append(h)

    if deleted:
        save_history(new_history)
        return jsonify({"message": "删除成功"})
    else:
        return jsonify({"error": "记录不存在或无权删除"}), 404


@app.route('/api/history/clear', methods=['POST'])
@require_auth
def clear_history():
    """清空历史记录"""
    username = request.session['username']
    role = request.session['role']

    if role == 'admin':
        save_history([])
    else:
        history = load_history()
        history = [h for h in history if h.get('username') != username]
        save_history(history)

    return jsonify({"message": "历史已清空"})


# ========== 用户管理 API（管理员） ==========

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def get_users():
    """获取所有用户"""
    users_data = load_users()
    users = []
    for username, info in users_data.get('users', {}).items():
        users.append({
            "username": username,
            "role": info.get('role', 'user'),
            "created_at": info.get('created_at', '')
        })
    return jsonify({"users": users})


@app.route('/api/admin/users/<username>/role', methods=['PUT'])
@require_admin
def update_user_role(username):
    """更新用户角色"""
    data = request.json
    new_role = data.get('role', 'user')

    if new_role not in ['admin', 'user']:
        return jsonify({"error": "无效的角色"}), 400

    users_data = load_users()
    if username not in users_data.get('users', {}):
        return jsonify({"error": "用户不存在"}), 404

    users_data['users'][username]['role'] = new_role
    save_users(users_data)

    # 更新已登录会话
    for token, session in sessions.items():
        if session.get('username') == username:
            session['role'] = new_role

    return jsonify({"message": "角色已更新"})


@app.route('/api/admin/users/<username>', methods=['DELETE'])
@require_admin
def delete_user(username):
    """删除用户"""
    if username == 'admin':
        return jsonify({"error": "不能删除管理员账户"}), 400

    users_data = load_users()
    if username not in users_data.get('users', {}):
        return jsonify({"error": "用户不存在"}), 404

    del users_data['users'][username]
    save_users(users_data)

    # 删除该用户的会话
    tokens_to_delete = [t for t, s in sessions.items() if s.get('username') == username]
    for t in tokens_to_delete:
        del sessions[t]

    return jsonify({"message": "用户已删除"})


# ========== 服务器控制函数（供GUI调用） ==========

def start_server(host: str = '0.0.0.0', port: int = 5000) -> tuple[bool, str]:
    """
    在后台线程中启动Web服务器
    返回: (成功与否, 消息)
    """
    global _server_thread, _server_running

    if _server_running:
        return False, "服务器已在运行中"

    # 检查前端是否已构建
    if not os.path.exists(app.static_folder):
        return False, "前端未构建，请先在 web_frontend 目录执行 npm run build"

    def run_server():
        global _server_running
        _server_running = True
        try:
            # 使用 werkzeug 的 serving 来运行，禁用重载器
            from werkzeug.serving import make_server
            server = make_server(host, port, app, threaded=True)
            server.serve_forever()
        except Exception as e:
            print(f"服务器错误: {e}")
        finally:
            _server_running = False

    _server_thread = Thread(target=run_server, daemon=True)
    _server_thread.start()

    return True, f"服务器已启动，访问地址: http://localhost:{port}"


def is_server_running() -> bool:
    """检查服务器是否正在运行"""
    return _server_running


def get_server_url(port: int = 5000) -> str:
    """获取服务器URL"""
    return f"http://localhost:{port}"


# ========== 主函数 ==========

def main():
    import argparse
    parser = argparse.ArgumentParser(description='专家系统 Web 服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()

    print("专家系统 Web 服务器启动中...")
    print(f"访问地址: http://localhost:{args.port}")
    print("默认管理员: admin / admin123")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
