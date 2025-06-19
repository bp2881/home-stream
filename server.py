from flask import Flask, request, jsonify, render_template, send_from_directory
from generate_media import list_videos, convert_to_mp4
import json

app = Flask(__name__)

@app.route('/')
def index():
    movie_list = json.load(open("./videos.json", "r")) 
    return render_template('index.html', movies=movie_list)

@app.route("/Watching")
def movies():
    return render_template("watch.html")


if __name__ == "__main__":
    #convert_to_mp4()  
    list_videos()
    app.run(debug=True, port=5000)
