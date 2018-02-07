import random
import uuid
import redis

import os
from flask import Flask, jsonify, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/test2.db')
print(app.config['SQLALCHEMY_DATABASE_URI'])
app.secret_key = 'super secret key'
db = SQLAlchemy(app)
redis_url = os.environ.get('REDIS_URL', "redis://localhost:6379/0")
cache = redis.from_url(redis_url)


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value_a = db.Column(db.String(), nullable=False)
    value_a_percent = db.Column(db.Float(), nullable=True)
    value_b = db.Column(db.String(), nullable=True)
    value_b_percent = db.Column(db.Float(), nullable=True)
    active = db.Column(db.Boolean(), default=True)

    def __repr__(self):
        return '<Config %r>' % self.key


@app.route('/init-db')
def init_db():
    db.drop_all()
    db.create_all()
    color_config = Config(key="color", value_a="red", value_a_percent=0.3, value_b="blue", value_b_percent=0.7)
    db.session.add(color_config)
    text_config = Config(key="text", value_a="text value a", value_a_percent=0, value_b="text value b", value_b_percent=1)
    db.session.add(text_config)
    inactive_config = Config(key="inactive config", value_a="Not active", value_a_percent=0.3, active=False)
    db.session.add(inactive_config)
    db.session.commit()
    return "Success"


@app.route('/api')
def api():
    session_id = request.cookies.get("session-id", None)
    if session_id and cache.get(session_id):
        return jsonify(cache.get(session_id))
    configs = Config.query.all()
    configs_dict = {}
    for c in configs:
        if c.active:
            configs_dict[
                c.key] = c.value_a if not c.value_b_percent and c.value_a_percent else c.value_a if random.random() <= c.value_a_percent / (
                c.value_a_percent + c.value_b_percent) else c.value_b
    response = jsonify(configs_dict)
    session_id = str(uuid.uuid4())
    cache.set(session_id, configs_dict)
    response.set_cookie("session-id", value=session_id)
    return response


@app.route("/")
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    admin = Admin(app, name='Remote Config Admin', template_mode='bootstrap3')
    admin.add_view(ModelView(Config, db.session))
    app.run()
