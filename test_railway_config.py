"""Railway config checks use inert URLs and never open a database connection."""

import os
import subprocess
import sys


CHECK_APP_CONFIG = """
import app
assert app.app.config['SQLALCHEMY_DATABASE_URI'].startswith('mysql+pymysql://')
assert app.app.config['APP_ENV'] == 'production'
assert app.app.config['DEBUG'] is False
assert app.app.config['SESSION_COOKIE_SECURE'] is True
"""


def run_config_check(extra_env):
    env = os.environ.copy()
    env['APP_ENV'] = 'production'
    env['FLASK_DEBUG'] = 'true'
    env['SECRET_KEY'] = 'railway-config-test-only-key'
    env.pop('RAILWAY_ENVIRONMENT_NAME', None)
    env.pop('RAILWAY_ENVIRONMENT', None)
    env.pop('DATABASE_URL', None)
    env.pop('MYSQL_URL', None)
    env.update(extra_env)
    result = subprocess.run(
        [sys.executable, '-c', CHECK_APP_CONFIG],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False
    )
    assert result.returncode == 0, 'Railway production configuration check failed.'


run_config_check({'DATABASE_URL': 'mysql://test:test@invalid.example:3306/college'})
run_config_check({'MYSQL_URL': 'mysql://test:test@invalid.example:3306/college'})

# Railway's documented environment marker must independently select production mode.
railway_env = os.environ.copy()
railway_env['APP_ENV'] = 'development'
railway_env['RAILWAY_ENVIRONMENT_NAME'] = 'production'
railway_env['FLASK_DEBUG'] = 'true'
railway_env['SECRET_KEY'] = 'railway-config-test-only-key'
railway_env.pop('DATABASE_URL', None)
railway_env['MYSQL_URL'] = 'mysql://test:test@invalid.example:3306/college'
result = subprocess.run(
    [sys.executable, '-c', CHECK_APP_CONFIG],
    env=railway_env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=False
)
assert result.returncode == 0, 'Railway environment marker did not enable production settings.'

print('PASS: DATABASE_URL, MYSQL_URL, Railway environment detection, secure cookies, and debug-off settings')
