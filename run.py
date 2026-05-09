import os, sys, time, threading, webbrowser, logging
from datetime import datetime

# ── Save raw stderr BEFORE eventlet patches it ────────
_raw_fd = os.dup(2)  # duplicate fd 2 (stderr)
_raw_stderr = os.fdopen(_raw_fd, 'w', buffering=1)

from app import create_app, init_db
from app.extensions import socketio

# Silence all noisy loggers — we have our own coloured request logs
for _name in ['werkzeug', 'eventlet.wsgi.server', 'engineio', 'socketio']:
    logging.getLogger(_name).setLevel(logging.ERROR)

app = create_app()

# Ensure the database and demo accounts are created even when running via Gunicorn
init_db(app)

# Suppress eventlet's raw WSGI request log lines (127.0.0.1 - - [...])
try:
    import eventlet.wsgi
    eventlet.wsgi.DEFAULT_LOG = type('_', (), {'write': lambda *a: None})()
except Exception:
    pass

# ── ANSI Colors ───────────────────────────────────────
C = {
    'GET': '\033[96m', 'POST': '\033[92m', 'PUT': '\033[93m',
    'DELETE': '\033[91m', 'PATCH': '\033[95m',
}
R  = '\033[0m'    # reset
B  = '\033[1m'    # bold
D  = '\033[2m'    # dim
G  = '\033[92m'   # green
Y  = '\033[33m'   # gold/yellow
RD = '\033[91m'   # red

def _log(msg):
    """Write directly to raw stderr — bypasses eventlet buffering."""
    _raw_stderr.write(msg + '\n')
    _raw_stderr.flush()


@app.before_request
def _before():
    from flask import g
    g._t0 = time.time()


@app.after_request
def _after(resp):
    from flask import request, g
    # Skip noise
    if '/static/' in request.path or '/socket.io/' in request.path:
        return resp
    ms = (time.time() - getattr(g, '_t0', time.time())) * 1000
    m  = request.method
    mc = C.get(m, '\033[97m')
    sc = G if resp.status_code < 300 else (Y if resp.status_code < 400 else RD)
    ts = datetime.now().strftime('%H:%M:%S')
    _log(f"  {D}{ts}{R}  {mc}{B}{m:<7}{R} {request.path:<42}  {sc}{B}{resp.status_code}{R}  {D}{ms:.0f}ms{R}")
    return resp


def get_local_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    _log(f"\n  {Y}{'━' * 53}{R}")
    _log(f"  {B}🎓  Aethelgard BCA Portal{R}  —  Python Flask + SQLite")
    _log(f"  {Y}{'━' * 53}{R}")
    _log(f"  💻  Local:   {B}http://127.0.0.1:5001{R}")
    _log(f"  🌐  Network: {B}http://{local_ip}:5001{R} (Share this link!)")
    _log(f"  📋  Demo:    {B}BCA2025001{R} / demo123")
    _log(f"  {Y}{'━' * 53}{R}")
    _log(f"  {D}Listening for requests...{R}\n")

    # Auto-open browser after server starts
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5001')
    threading.Thread(target=open_browser, daemon=True).start()

    _null_log = open(os.devnull, 'w')
    socketio.run(app, debug=True, host='0.0.0.0', port=5001,
                 allow_unsafe_werkzeug=True, log_output=False)
