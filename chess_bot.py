import os
import io
import json
import time
import cv2
import numpy as np
import requests
import chess
import chess.pgn
import chess.svg
from PIL import Image
from datetime import datetime
import tempfile
import subprocess

# Configuration
USERNAME = "rohitsharma740431"
VIDEO_FILENAME = "chess_game.mp4"
FINAL_VIDEO_FILENAME = "chess_short.mp4"
BACKGROUND_MUSIC = "background.mp3"

# Check if Inkscape is installed
def check_inkscape():
    try:
        result = subprocess.run(["inkscape", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✔️ Inkscape is installed.")
            return True
    except FileNotFoundError:
        print("❌ Inkscape is not installed or not found.")
        return False

# Check if FFmpeg is installed
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✔️ FFmpeg is installed.")
        return True
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not found.")
        return False

# Fetch Chess.com game data
def fetch_latest_game(username):
    current_year = datetime.now().year
    current_month = str(datetime.now().month).zfill(2)
    url = f"https://api.chess.com/pub/player/{username}/games/{current_year}/{current_month}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:    
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("games", [])
    except requests.RequestException as e:
        print(f"❌ Failed to fetch data: {e}")
        return []

# Convert SVG to PNG using Inkscape
def svg_to_png(svg_code):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as temp_svg:
            temp_svg.write(svg_code.encode("utf-8"))
            temp_svg_path = temp_svg.name
        
        temp_png_path = temp_svg_path.replace(".svg", ".png")
        command = ["inkscape", "--export-filename", temp_png_path, temp_svg_path]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            return Image.open(temp_png_path)
        else:
            print("❌ Inkscape conversion failed!")
            return None
    except FileNotFoundError:
        print("❌ Inkscape is not installed or not found!")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Error converting SVG to PNG: {e}")
        return None

# Generate a video from chess moves
def generate_video(game_pgn, output_filename):
    game = chess.pgn.read_game(io.StringIO(game_pgn))
    if not game:
        print("❌ Error parsing PGN!")
        return False
    
    board = game.board()
    frames = []
    
    for move in game.mainline_moves():
        board.push(move)
        board_svg = chess.svg.board(board)
        img = svg_to_png(board_svg)
        if img:
            frames.append(img)
    
    if not frames:
        print("❌ No frames generated!")
        return False
    
    frame_width, frame_height = frames[0].size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_filename, fourcc, 2, (frame_width, frame_height))
    
    for frame in frames:
        img_array = np.array(frame)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        video.write(img_bgr)
    
    video.release()
    print(f"✔️ Video created: {output_filename}")
    return True

# Add background music to the video (Only if MP3 exists)
def add_audio(video_filename, music_filename, output_filename):
    if not os.path.exists(music_filename):
        print("⚠️ No background music found. Skipping audio merging.")
        os.rename(video_filename, output_filename)
        print(f"✔️ Final video saved as: {output_filename}")
        return True
    
    try:
        command = [
            'ffmpeg', '-i', video_filename, '-i', music_filename,
            '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', output_filename
        ]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print(f"✔️ Chess video with audio generated: {output_filename}")
            return True
        else:
            print("❌ FFmpeg audio merging failed!")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not found!")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error adding audio: {e}")
        return False

# Convert video to 9:16 Shorts format while preserving full board
def convert_to_short_format(input_video, output_video):
    try:
        command = [
            'ffmpeg', '-i', input_video,
            '-vf', 'scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:black',
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            output_video
        ]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            print(f"✔️ Video converted to Shorts format with full board: {output_video}")
            return True
        else:
            print("❌ Failed to convert video format properly!")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not found!")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error converting video: {e}")
        return False

# Main execution
def main():
    if not check_inkscape():
        print("⚠️ Inkscape is not installed. Skipping video creation.")
        return
    
    if not check_ffmpeg():
        print("⚠️ FFmpeg is not installed. Skipping video creation.")
        return

    games = fetch_latest_game(USERNAME)
    if games:
        latest_game = games[-1].get("pgn", "").strip()
        if latest_game:
            if generate_video(latest_game, VIDEO_FILENAME):
                if add_audio(VIDEO_FILENAME, BACKGROUND_MUSIC, FINAL_VIDEO_FILENAME):
                    convert_to_short_format(FINAL_VIDEO_FILENAME, "chess_final_short.mp4")
        else:
            print("❌ PGN data is empty!")
    else:
        print("❌ No games found!")

if __name__ == "__main__":
    main()
