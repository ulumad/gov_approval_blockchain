from flask import Flask, request, jsonify, render_template, session, g
from flask_cors import CORS
import threading
import time
import secrets
from blockchain import approval_system
from auth import auth_manager, Permission

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)


def get_current_user():
    """从session获取当前登录用户"""
    if 'username' not in session:
        return None
    return auth_manager.get_user(session['username'])


@app.before_request
def before_request():
    """每个请求前设置当前用户"""
    g.user = get_current_user()


# ==================== 页面路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


@app.route('/templates')
def templates_page():
    return render_template('templates.html')


# ==================== API路由 - 认证 ====================

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    success, result = auth_manager.verify_login(username, password)
    if success:
        session['username'] = username
        user = result
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'username': user.username,
                'role': user.role,
                'permissions': user.permissions
            }
        })
    return jsonify({'success': False, 'message': result}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'success': True, 'message': '登出成功'})


@app.route('/api/current-user', methods=['GET'])
def get_current_user_api():
    user = g.user
    if user:
        return jsonify({
            'success': True,
            'user': {
                'username': user.username,
                'role': user.role,
                'permissions': user.permissions
            }
        })
    return jsonify({'success': False, 'message': '未登录'}), 401


# ==================== API路由 - 用户管理（超级管理员） ====================

@app.route('/api/users', methods=['GET'])
def get_users():
    user = g.user
    if not user or not auth_manager.is_super_admin(user):
        return jsonify({'success': False, 'message': '无权限'}), 403
    users = auth_manager.get_all_users(user)
    return jsonify({'success': True, 'users': users})


@app.route('/api/users', methods=['POST'])
def create_user():
    user = g.user
    if not user or not auth_manager.is_super_admin(user):
        return jsonify({'success': False, 'message': '无权限'}), 403

    data = request.json
    username = data.get('username')
    password = data.get('password')
    permissions = data.get('permissions', [])

    success, message = auth_manager.create_user(user, username, password, permissions)
    return jsonify({'success': success, 'message': message})


@app.route('/api/users/<username>/permissions', methods=['PUT'])
def update_permissions(username):
    user = g.user
    if not user or not auth_manager.is_super_admin(user):
        return jsonify({'success': False, 'message': '无权限'}), 403

    data = request.json
    permissions = data.get('permissions', [])

    success, message = auth_manager.update_user_permissions(user, username, permissions)
    return jsonify({'success': success, 'message': message})


@app.route('/api/users/<username>/password', methods=['PUT'])
def update_password(username):
    user = g.user
    if not user or not auth_manager.is_super_admin(user):
        return jsonify({'success': False, 'message': '无权限'}), 403

    data = request.json
    new_password = data.get('new_password')

    success, message = auth_manager.update_user_password(user, username, new_password)
    return jsonify({'success': success, 'message': message})


@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    user = g.user
    if not user or not auth_manager.is_super_admin(user):
        return jsonify({'success': False, 'message': '无权限'}), 403

    success, message = auth_manager.delete_user(user, username)
    return jsonify({'success': success, 'message': message})


@app.route('/api/permissions', methods=['GET'])
def get_permissions():
    permissions = auth_manager.get_all_permissions()
    return jsonify({'success': True, 'permissions': permissions})


# ==================== API路由 - 模板管理 ====================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    templates = approval_system.get_user_templates(user.username)
    return jsonify({'success': True, 'templates': templates})


@app.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    template = approval_system.get_template(template_id, user.username)
    if not template:
        return jsonify({'success': False, 'message': '模板不存在或无权限访问'}), 404

    return jsonify({'success': True, 'template': template})


@app.route('/api/templates', methods=['POST'])
def create_template():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.json
    name = data.get('name')
    fields = data.get('fields', [])
    content = data.get('content', [])

    if not name:
        return jsonify({'success': False, 'message': '模板名称不能为空'}), 400

    template_id, template = approval_system.create_template(name, fields, user.username, content)
    return jsonify({
        'success': True,
        'message': '模板创建成功',
        'template': template
    })


@app.route('/api/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.json
    name = data.get('name')
    fields = data.get('fields')
    content = data.get('content')

    template_id, template = approval_system.update_template(
        template_id,
        name=name,
        fields=fields,
        content=content,
        owner=user.username
    )

    if template_id is None:
        return jsonify({'success': False, 'message': template}), 400

    return jsonify({
        'success': True,
        'message': '模板更新成功',
        'template': template
    })


@app.route('/api/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    success, message = approval_system.delete_template(template_id, user.username)
    if not success:
        return jsonify({'success': False, 'message': message}), 400

    return jsonify({'success': True, 'message': message})


# ==================== API路由 - 政务审批 ====================

@app.route('/api/applications', methods=['POST'])
def create_application():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    if not user.can_process_stage('apply'):
        return jsonify({'success': False, 'message': '无申请权限'}), 403

    data = request.json
    title = data.get('title')
    content = data.get('content')
    template_id = data.get('template_id')

    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400

    application, mine_func = approval_system.create_application(
        title=title,
        content=content,
        applicant=user.username,
        template_id=template_id
    )

    return jsonify({
        'success': True,
        'message': '申请创建成功',
        'application': application,
        'mining_required': True
    })


@app.route('/api/applications/mine', methods=['POST'])
def mine_application():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.json
    app_id = data.get('app_id')
    mine_type = data.get('type')

    result = {'done': False, 'data': None}

    def mining_thread():
        try:
            if mine_type == 'create':
                app_data = data.get('application_data', {})
                application, mine_func = approval_system.create_application(
                    title=app_data.get('title'),
                    content=app_data.get('content'),
                    applicant=user.username,
                    template_id=app_data.get('template_id')
                )
                block = mine_func()
                result['data'] = {'success': True, 'block_hash': block.hash, 'block_index': block.index}
            else:
                mine_func = data.get('mine_func')
                if mine_func:
                    block, app = mine_func()
                    result['data'] = {'success': True, 'block_hash': block.hash, 'block_index': block.index}
            result['done'] = True
        except Exception as e:
            result['data'] = {'success': False, 'message': str(e)}
            result['done'] = True

    thread = threading.Thread(target=mining_thread)
    thread.start()
    thread.join()

    return jsonify(result['data'])


@app.route('/api/applications/<app_id>/process', methods=['POST'])
def process_application(app_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    application = approval_system.get_application(app_id)
    if not application:
        return jsonify({'success': False, 'message': '申请不存在'}), 404

    current_stage = application['current_stage']

    if not user.can_process_stage(current_stage):
        return jsonify({'success': False, 'message': f'无{current_stage}阶段权限'}), 403

    data = request.json
    action = data.get('action', '通过')
    comment = data.get('comment', '')

    mine_func, error = approval_system.process_application(app_id, user.username, action, comment)
    if error:
        return jsonify({'success': False, 'message': error}), 400

    return jsonify({
        'success': True,
        'message': '流程处理成功',
        'mining_required': True,
        'mine_data': {
            'app_id': app_id,
            'type': 'process'
        }
    })


@app.route('/api/applications/<app_id>/mine', methods=['POST'])
def mine_process_application(app_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    data = request.json
    action = data.get('action', '通过')
    comment = data.get('comment', '')

    result = {'done': False, 'data': None}

    def mining_thread():
        try:
            mine_func, error = approval_system.process_application(app_id, user.username, action, comment)
            if error:
                result['data'] = {'success': False, 'message': error}
            else:
                block, app = mine_func()
                result['data'] = {
                    'success': True,
                    'block_hash': block.hash,
                    'block_index': block.index,
                    'application': app
                }
            result['done'] = True
        except Exception as e:
            result['data'] = {'success': False, 'message': str(e)}
            result['done'] = True

    thread = threading.Thread(target=mining_thread)
    thread.start()
    thread.join()

    return jsonify(result['data'])


@app.route('/api/applications', methods=['GET'])
def get_applications():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    all_apps = approval_system.get_all_applications()

    pending_apps = []
    for app in all_apps:
        if app['status'] != 'completed' and user.can_process_stage(app['current_stage']):
            pending_apps.append(app)

    return jsonify({
        'success': True,
        'all_applications': all_apps,
        'pending_applications': pending_apps
    })


@app.route('/api/applications/<app_id>', methods=['GET'])
def get_application(app_id):
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    application = approval_system.get_application(app_id)
    if not application:
        return jsonify({'success': False, 'message': '申请不存在'}), 404

    return jsonify({'success': True, 'application': application})


@app.route('/api/blockchain/info', methods=['GET'])
def get_blockchain_info():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    info = approval_system.get_blockchain_info()
    return jsonify({'success': True, 'info': info})


@app.route('/api/blockchain/transactions', methods=['GET'])
def get_transactions():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    transactions = approval_system.blockchain.get_all_transactions()
    return jsonify({'success': True, 'transactions': transactions})


@app.route('/api/blockchain/transactions/search', methods=['GET'])
def search_transactions():
    user = g.user
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401

    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)
    operator = request.args.get('operator', None)
    stage = request.args.get('stage', None)

    transactions = approval_system.blockchain.search_transactions(
        start_time=start_time,
        end_time=end_time,
        operator=operator,
        stage=stage
    )

    return jsonify({
        'success': True, 
        'transactions': transactions,
        'count': len(transactions)
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
