from flask import Flask, request, jsonify, render_template, send_from_directory
from generate_media import list_videos, convert_to_mp4

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route("/<path:filename>")
def serve_video(filename):
    return send_from_directory("media/", filename)

@app.route("/movies")
def movies():
    return render_template("movies.html")


if __name__ == "__main__":
    #convert_to_mp4()  
    list_videos()
    app.run(host='127.0.0.1', debug=True, port=2005)