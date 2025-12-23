"""专家系统 Web 服务器"""

import os
import sys
import uuid
from datetime import datetime
from functools import wraps
from threading import Thread

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from src.core import RuleReasoner
from src.data import DataStorage

# 确定静态文件路径
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_static_folder = os.path.join(_base, "frontend", "dist")

# 检查静态文件夹是否存在，不存在则使用空字符串（启动时会检查）
if not os.path.exists(_static_folder):
    _static_folder = _static_folder  # 保持路径，启动时检查

app = Flask(__name__, static_folder=_static_folder, static_url_path="")
CORS(app)

# 路由处理：SPA 支持
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# 服务器运行状态
_server_thread = None
_server_running = False

# 数据存储
storage = DataStorage()

# 会话管理
sessions: dict = {}


def get_session(token: str):
    return sessions.get(token)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        session = get_session(token)
        if not session:
            return jsonify({"error": "未授权访问"}), 401
        request.session = session
        return f(*args, **kwargs)

    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        session = get_session(token)
        if not session:
            return jsonify({"error": "未授权访问"}), 401
        if session.get("role") != "admin":
            return jsonify({"error": "需要管理员权限"}), 403
        request.session = session
        return f(*args, **kwargs)

    return decorated


class ReasonerSession:
    """每个用户会话的推理器状态"""

    def __init__(self):
        self.reasoner = RuleReasoner()
        self.rules = storage.load_rules()
        self.reasoner.reset(self.rules)
        self.known_facts = [[], []]
        self.false_facts = []
        self.path_all = []
        self.backward_target = None
        self.backward_in_progress = False

    def reset_state(self):
        self.reasoner.clear_known()
        self.reasoner.clear_false()
        self.known_facts = [[], []]
        self.false_facts = []
        self.path_all = []
        self.backward_target = None
        self.backward_in_progress = False

    def reload_rules(self):
        self.rules = storage.load_rules()
        self.reasoner.reset(self.rules)

    def get_all_atoms(self) -> set:
        atoms, conclusions = set(), set()
        for pres, ans in self.rules:
            atoms.update(pres)
            conclusions.add(ans)
        return atoms - conclusions

    def get_all_conclusions(self) -> set:
        return {ans for _, ans in self.rules}


def get_reasoner_session(session: dict) -> ReasonerSession:
    if "reasoner_session" not in session:
        session["reasoner_session"] = ReasonerSession()
    return session["reasoner_session"]


def _reload_all_reasoner_sessions():
    """刷新所有会话的推理器规则"""
    for session in sessions.values():
        if "reasoner_session" in session:
            session["reasoner_session"].reload_rules()


# ========== 路由 ==========


@app.route("/")
def index():
    """服务前端首页"""
    if not app.static_folder or not os.path.exists(app.static_folder):
        return (
            jsonify({"error": "前端未构建，请先在 web_frontend 目录执行 pnpm build"}),
            500,
        )
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """服务静态文件，支持 SPA 路由"""
    if not app.static_folder:
        return jsonify({"error": "前端未构建"}), 500
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    # SPA 路由回退到 index.html
    return send_from_directory(app.static_folder, "index.html")


# ========== 认证 API ==========


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "")
    password = data.get("password", "")

    users_data = storage.load_users()
    user = users_data.get("users", {}).get(username)

    if not user or user["password"] != password:
        return jsonify({"error": "用户名或密码错误"}), 401

    token = str(uuid.uuid4())
    sessions[token] = {
        "username": username,
        "role": user["role"],
        "login_time": datetime.now().isoformat(),
    }
    return jsonify({"token": token, "username": username, "role": user["role"]})


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    users_data = storage.load_users()
    if username in users_data.get("users", {}):
        return jsonify({"error": "用户名已存在"}), 400

    users_data["users"][username] = {
        "password": password,
        "role": "user",
        "created_at": datetime.now().isoformat(),
    }
    storage.save_users(users_data)
    return jsonify({"message": "注册成功"})


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    sessions.pop(token, None)
    return jsonify({"message": "已登出"})


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    return jsonify(
        {"username": request.session["username"], "role": request.session["role"]}
    )


# ========== 规则 API ==========


@app.route("/api/rules", methods=["GET"])
def get_rules():
    rules = storage.load_rules()
    return jsonify(
        {
            "rules": [
                {"id": i, "premises": pres, "conclusion": ans}
                for i, (pres, ans) in enumerate(rules)
            ]
        }
    )


@app.route("/api/rules", methods=["POST"])
@require_admin
def add_rule():
    data = request.json
    premises = data.get("premises", [])
    conclusion = data.get("conclusion", "")

    if not premises or not conclusion:
        return jsonify({"error": "前提和结论不能为空"}), 400

    rules = storage.load_rules()
    rules.append((premises, conclusion))
    storage.save_rules(rules)
    _reload_all_reasoner_sessions()

    return jsonify({"message": "规则添加成功", "id": len(rules) - 1})


@app.route("/api/rules/batch", methods=["POST"])
@require_admin
def batch_add_rules():
    """批量添加规则"""
    data = request.json
    new_rules = data.get("rules", [])

    if not new_rules:
        return jsonify({"error": "规则列表不能为空"}), 400

    rules = storage.load_rules()
    added_count = 0
    for rule in new_rules:
        premises = rule.get("premises", [])
        conclusion = rule.get("conclusion", "")
        if premises and conclusion:
            rules.append((premises, conclusion))
            added_count += 1

    storage.save_rules(rules)
    _reload_all_reasoner_sessions()

    return jsonify({"message": f"成功添加 {added_count} 条规则"})


@app.route("/api/rules/<int:rule_id>", methods=["PUT"])
@require_admin
def update_rule(rule_id):
    data = request.json
    premises = data.get("premises", [])
    conclusion = data.get("conclusion", "")

    if not premises or not conclusion:
        return jsonify({"error": "前提和结论不能为空"}), 400

    rules = storage.load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        return jsonify({"error": "规则不存在"}), 404

    rules[rule_id] = (premises, conclusion)
    storage.save_rules(rules)
    _reload_all_reasoner_sessions()

    return jsonify({"message": "规则更新成功"})


@app.route("/api/rules/<int:rule_id>", methods=["DELETE"])
@require_admin
def delete_rule(rule_id):
    rules = storage.load_rules()
    if rule_id < 0 or rule_id >= len(rules):
        return jsonify({"error": "规则不存在"}), 404

    rules.pop(rule_id)
    storage.save_rules(rules)
    _reload_all_reasoner_sessions()

    return jsonify({"message": "规则删除成功"})


@app.route("/api/rules/reset", methods=["POST"])
@require_admin
def reset_rules():
    from src.data import DEFAULT_RULES

    rules = [(list(pres), ans) for pres, ans in DEFAULT_RULES]
    storage.save_rules(rules)
    _reload_all_reasoner_sessions()

    return jsonify({"message": "规则已重置"})


# ========== 事实 API ==========


@app.route("/api/facts/atoms", methods=["GET"])
@require_auth
def get_atoms():
    rs = get_reasoner_session(request.session)
    return jsonify({"atoms": sorted(rs.get_all_atoms())})


@app.route("/api/facts/conclusions", methods=["GET"])
@require_auth
def get_conclusions():
    rs = get_reasoner_session(request.session)
    return jsonify({"conclusions": sorted(rs.get_all_conclusions())})


@app.route("/api/facts/known", methods=["GET"])
@require_auth
def get_known_facts():
    rs = get_reasoner_session(request.session)
    return jsonify(
        {"user_facts": rs.known_facts[0], "derived_facts": rs.known_facts[1]}
    )


@app.route("/api/facts/known", methods=["POST"])
@require_auth
def set_known_facts():
    data = request.json
    facts = data.get("facts", [])
    rs = get_reasoner_session(request.session)

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


@app.route("/api/facts/clear", methods=["POST"])
@require_auth
def clear_facts():
    rs = get_reasoner_session(request.session)
    rs.reset_state()
    return jsonify({"message": "事实已清空"})


@app.route("/api/facts/false", methods=["GET"])
@require_auth
def get_false_facts():
    """获取已知为假的事实"""
    rs = get_reasoner_session(request.session)
    return jsonify({"facts": rs.false_facts})


@app.route("/api/facts/false", methods=["POST"])
@require_auth
def set_false_facts():
    """设置已知为假的事实"""
    data = request.json
    facts = data.get("facts", [])
    rs = get_reasoner_session(request.session)

    rs.false_facts = facts
    rs.reasoner.clear_false()
    if facts:
        rs.reasoner.add_false(facts)

    return jsonify({"message": "事实已更新"})


# ========== 推理 API ==========


@app.route("/api/inference/forward", methods=["POST"])
@require_auth
def forward_inference():
    rs = get_reasoner_session(request.session)

    if not rs.known_facts[0]:
        return jsonify({"error": "请先添加已知事实"}), 400

    conclusions, path = rs.reasoner.find()
    rs.path_all += [r for r in path if r not in rs.path_all]

    for rule_id in path:
        if rule_id < len(rs.rules):
            derived = rs.rules[rule_id][1]
            if derived not in rs.known_facts[1]:
                rs.known_facts[1].append(derived)

    result = {
        "conclusions": conclusions,
        "path": rs.path_all,
        "rules": [
            {"id": i, "premises": pres, "conclusion": ans}
            for i, (pres, ans) in enumerate(rs.rules)
        ],
        "known_facts": rs.known_facts[0],
        "derived_facts": rs.known_facts[1],
    }

    if conclusions:
        storage.add_history(
            {
                "id": str(uuid.uuid4()),
                "username": request.session["username"],
                "type": "forward",
                "facts": rs.known_facts[0],
                "conclusion": conclusions[0],
                "path": rs.path_all,
                "timestamp": datetime.now().isoformat(),
            }
        )

    return jsonify(result)


@app.route("/api/inference/backward/start", methods=["POST"])
@require_auth
def start_backward():
    data = request.json
    target = data.get("target", "")

    if not target:
        return jsonify({"error": "请指定目标结论"}), 400

    rs = get_reasoner_session(request.session)
    rs.backward_target = target
    rs.backward_in_progress = True

    return _continue_backward_internal(rs, request.session)


@app.route("/api/inference/backward/continue", methods=["POST"])
@require_auth
def continue_backward():
    data = request.json
    true_facts = data.get("true_facts", [])
    false_facts = data.get("false_facts", [])

    rs = get_reasoner_session(request.session)

    if not rs.backward_in_progress:
        return jsonify({"error": "没有进行中的反向推理"}), 400

    if true_facts:
        rs.reasoner.add_known(true_facts)
        rs.known_facts[0].extend(true_facts)

    if false_facts:
        rs.reasoner.add_false(false_facts)
        rs.false_facts.extend(false_facts)

    return _continue_backward_internal(rs, request.session)


def _continue_backward_internal(rs: ReasonerSession, session: dict):
    status, data, path = rs.reasoner.step_backward(rs.backward_target)
    rs.path_all += [r for r in path if r not in rs.path_all]

    for rule_id in path:
        if rule_id < len(rs.rules):
            derived = rs.rules[rule_id][1]
            if derived not in rs.known_facts[1]:
                rs.known_facts[1].append(derived)

    result = {
        "path": rs.path_all,
        "rules": [
            {"id": i, "premises": pres, "conclusion": ans}
            for i, (pres, ans) in enumerate(rs.rules)
        ],
        "known_facts": rs.known_facts[0],
        "derived_facts": rs.known_facts[1],
        "target": rs.backward_target,
    }

    if status == 0:
        rs.backward_in_progress = False
        result["status"] = "success"
        result["message"] = f"目标 '{rs.backward_target}' 已证明成立"
        storage.add_history(
            {
                "id": str(uuid.uuid4()),
                "username": session["username"],
                "type": "backward",
                "facts": rs.known_facts[0],
                "conclusion": rs.backward_target,
                "path": rs.path_all,
                "timestamp": datetime.now().isoformat(),
            }
        )
    elif status == 1:
        rs.backward_in_progress = False
        result["status"] = "failed"
        result["message"] = f"无法证明目标 '{rs.backward_target}' 成立"
    elif status == 2:
        result["status"] = "query"
        result["query_facts"] = [f for f in data if f not in rs.known_facts[0]]
        result["message"] = "需要确认以下事实"

    return jsonify(result)


# ========== 历史记录 API ==========


@app.route("/api/history", methods=["GET"])
@require_auth
def get_history():
    history = storage.load_history()
    username = request.session["username"]
    role = request.session["role"]

    if role != "admin":
        history = [h for h in history if h.get("username") == username]

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    total = len(history)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify(
        {
            "history": list(reversed(history[start:end])),
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@app.route("/api/history/<history_id>", methods=["DELETE"])
@require_auth
def delete_history(history_id):
    history = storage.load_history()
    username = request.session["username"]
    role = request.session["role"]

    new_history = []
    deleted = False
    for h in history:
        if h.get("id") == history_id:
            if role == "admin" or h.get("username") == username:
                deleted = True
                continue
        new_history.append(h)

    if deleted:
        storage.save_history(new_history)
        return jsonify({"message": "删除成功"})
    return jsonify({"error": "记录不存在或无权删除"}), 404


@app.route("/api/history/clear", methods=["POST"])
@require_auth
def clear_history():
    username = request.session["username"]
    role = request.session["role"]

    if role == "admin":
        storage.save_history([])
    else:
        history = storage.load_history()
        history = [h for h in history if h.get("username") != username]
        storage.save_history(history)

    return jsonify({"message": "历史已清空"})


# ========== 用户管理 API ==========


@app.route("/api/admin/users", methods=["GET"])
@require_admin
def get_users():
    users_data = storage.load_users()
    users = [
        {
            "username": u,
            "role": info.get("role", "user"),
            "created_at": info.get("created_at", ""),
        }
        for u, info in users_data.get("users", {}).items()
    ]
    return jsonify({"users": users})


@app.route("/api/admin/users/<username>/role", methods=["PUT"])
@require_admin
def update_user_role(username):
    data = request.json
    new_role = data.get("role", "user")

    if new_role not in ["admin", "user"]:
        return jsonify({"error": "无效的角色"}), 400

    users_data = storage.load_users()
    if username not in users_data.get("users", {}):
        return jsonify({"error": "用户不存在"}), 404

    users_data["users"][username]["role"] = new_role
    storage.save_users(users_data)

    for session in sessions.values():
        if session.get("username") == username:
            session["role"] = new_role

    return jsonify({"message": "角色已更新"})


@app.route("/api/admin/users/<username>", methods=["DELETE"])
@require_admin
def delete_user(username):
    if username == "admin":
        return jsonify({"error": "不能删除管理员账户"}), 400

    users_data = storage.load_users()
    if username not in users_data.get("users", {}):
        return jsonify({"error": "用户不存在"}), 404

    del users_data["users"][username]
    storage.save_users(users_data)

    tokens_to_delete = [t for t, s in sessions.items() if s.get("username") == username]
    for t in tokens_to_delete:
        del sessions[t]

    return jsonify({"message": "用户已删除"})


# ========== 服务器控制 ==========


def start_server(host: str = "0.0.0.0", port: int = 5000) -> tuple[bool, str]:
    """在后台线程中启动Web服务器"""
    global _server_thread, _server_running

    if _server_running:
        return False, "服务器已在运行中"

    if not os.path.exists(app.static_folder):
        return False, "前端未构建，请先在 frontend 目录执行 pnpm build"

    def run_server():
        global _server_running
        _server_running = True
        try:
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
    return _server_running


def run_standalone(host: str = "0.0.0.0", port: int = 5000):
    """独立运行Web服务器"""
    print("=" * 50)
    print("  专家系统 - Web服务器模式")
    print("=" * 50)
    print(f"访问地址: http://localhost:{port}")
    print("默认管理员: admin / admin123")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    app.run(host=host, port=port, debug=False)
