import logging
import os
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
)
import media_manager
from config import CHUNK_SIZE, HOST, PORT, SUBS_DIR, THUMB_DIR, WATCHER_INTERVAL
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("home-stream")
app = Flask(__name__)
@app.template_filter("duration")
def duration_filter(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"
@app.route("/")
def index():
    items = media_manager.get_all()
    return render_template("index.html", items=items)
@app.route("/watch/<media_id>")
def watch(media_id: str):
    item = media_manager.get_item(media_id)
    if item is None:
        abort(404)
    if item.converting:
        return render_template("index.html", items=media_manager.get_all(),
                               flash=f'"{item.title}" is still converting.')
    return render_template("watch.html", item=item)
@app.route("/stream/<media_id>")
def stream(media_id: str):
    item = media_manager.get_item(media_id)
    if item is None:
        abort(404)
    path = item.path
    if not os.path.exists(path):
        abort(404)
    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range")
    if range_header:
        parts = range_header.replace("bytes=", "").split("-")
        start = int(parts[0]) if parts[0] else 0
        end   = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end   = min(end, file_size - 1)
        status = 206
    else:
        start, end = 0, file_size - 1
        status = 200
    length = end - start + 1
    ext    = os.path.splitext(path)[1].lower()
    mime   = "video/webm" if ext == ".webm" else "video/mp4"

    # ── Nginx X-Accel-Redirect (zero-copy, no Python I/O) ─────────────────
    # When behind Nginx, return only headers; Nginx serves the file via its
    # internal /media-internal/ alias (kernel sendfile, aio threads).
    # Nginx sets the X-Real-IP header on proxied requests; use it as a signal.
    if request.headers.get("X-Real-IP") or os.environ.get("HOMESTREAM_BEHIND_NGINX"):
        # Convert absolute fs path → Nginx internal URI:
        #   /home/.../home-stream/cache/converted/abc.mp4
        #   → /media-internal/cache/converted/abc.mp4
        project_root = os.path.dirname(os.path.abspath(__file__))
        rel_path = os.path.relpath(path, project_root)
        nginx_uri = f"/media-internal/{rel_path}"
        resp = Response(status=status)
        resp.headers["X-Accel-Redirect"]  = nginx_uri
        resp.headers["X-Accel-Buffering"] = "yes"
        resp.headers["Content-Type"]      = mime
        resp.headers["Content-Length"]    = str(length)
        resp.headers["Content-Range"]     = f"bytes {start}-{end}/{file_size}"
        resp.headers["Accept-Ranges"]     = "bytes"
        resp.headers["Cache-Control"]     = "no-store"
        return resp

    # ── Pure-Python fallback (dev server / no Nginx) ───────────────────────
    def generate():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range":  f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges":  "bytes",
        "Content-Length": str(length),
        "Content-Type":   mime,
        "Cache-Control":  "no-store",
    }
    return Response(generate(), status=status, headers=headers)
@app.route("/thumb/<media_id>")
def thumb(media_id: str):
    path = os.path.join(THUMB_DIR, f"{media_id}.jpg")
    if not os.path.exists(path):
        abort(404)
    return Response(open(path, "rb").read(), mimetype="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})
@app.route("/subs/<media_id>/<int:track_idx>")
def subs(media_id: str, track_idx: int):
    item = media_manager.get_item(media_id)
    if item is None:
        abort(404)
    matched = [t for t in item.sub_tracks if t.index == track_idx]
    if not matched:
        abort(404)
    vtt_path = matched[0].vtt_path
    if not os.path.exists(vtt_path):
        abort(404)
    return Response(
        open(vtt_path, "r", errors="replace").read(),
        mimetype="text/vtt",
        headers={"Access-Control-Allow-Origin": "*"},
    )
@app.route("/api/library")
def api_library():
    return jsonify(media_manager.library_as_json())
@app.route("/api/debug/<media_id>")
def api_debug(media_id: str):
    item = media_manager.get_item(media_id)
    if item is None:
        return jsonify({"error": "not found"}), 404
    tracks = []
    for t in item.sub_tracks:
        tracks.append({
            "index":    t.index,
            "language": t.language,
            "label":    t.label,
            "vtt_path": t.vtt_path,
            "vtt_exists": os.path.exists(t.vtt_path),
            "vtt_size":   os.path.getsize(t.vtt_path) if os.path.exists(t.vtt_path) else 0,
            "url":      f"/subs/{media_id}/{t.index}",
        })
    return jsonify({
        "id":         item.id,
        "title":      item.title,
        "path":       item.path,
        "converting": item.converting,
        "sub_tracks": tracks,
    })
@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    media_manager.scan()
    return jsonify({"ok": True, "count": len(media_manager.get_all())})
if __name__ == "__main__":
    log.info("Scanning media library…")
    media_manager.scan()
    log.info("Starting FileWatcher (interval=%ds)…", WATCHER_INTERVAL)
    media_manager.start_watcher(interval=WATCHER_INTERVAL)
    log.info("Starting HOME-STREAM on %s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False, threaded=True)