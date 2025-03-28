import subprocess
from elevenlabs import ElevenLabs
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings
import random
import os
import requests
import json
from pathlib import Path
from typing import Optional

prompt = "New Discoveries in the Pyramids of Gyza" 
audio_path = "scenario_audio.mp3"  
json_path = "transcription.json"
videos_folder = "./videos"
ass_path = "subtitles.ass"
output_video_path = "final_video_with_subtitles.mp4"
api_key_11labs = "sk_9a0669fc3f70a85f53d79c7fd8a768a5b92225414dd1d496"
voice_id="20zUtLxCwVzsFDWub4sB"

#Step 1: Video Choice
def get_video_duration(videos_folder: str) -> tuple[Optional[str], Optional[float]]:
    video_files = [f for f in os.listdir(videos_folder) if f.endswith(".mp4")]
    if not video_files:
        print("Error: No .mp4 files found in the videos folder.")
        return None, None
    
    video_path = os.path.join(videos_folder, random.choice(video_files))
    try:
        video_clip = VideoFileClip(video_path)
        return video_path, video_clip.duration
    except Exception as e:
        print(f"Error loading video: {e}")
        return None, None

video_path, video_duration = get_video_duration(videos_folder)
if video_path:
    print(f"Selected video: {video_path}, Duration: {video_duration} seconds")

#Step 2: Scenario Generation
def generate_scenario(prompt: str, duration: float) -> Optional[str]:
    target_word_count = max(30, min(120, int(duration * 2.25)))  # Greek speech rate
    print(f"Target word count: {target_word_count} words")
    
    model_prompt = (
        f"Create a concise first-person monologue about '{prompt}' in Greek. "
        f"Max {target_word_count} words. Use short sentences."
    )
    try:
        result = subprocess.run(
            ["ollama", "run", "ilsp/meltemi-instruct-v1.5", model_prompt],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error generating scenario: {e}")
        return None

scenario = generate_scenario(prompt, video_duration) if video_duration else None
if scenario:
    print("Scenario generated:", scenario)

#Step 3: Audio From 11Labs
def generate_audio(scenario: str, output_path: str, api_key: str, voice_id: str) -> bool:
    client = ElevenLabs(api_key=api_key)
    try:
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=scenario,
            model_id="eleven_multilingual_v2"
        )
        with open(output_path, "wb") as audio_file:
            for chunk in audio_generator:
                audio_file.write(chunk)
        print(f"Audio saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error generating audio: {e}")
        return False

audio_success = generate_audio(scenario, audio_path, api_key_11labs, voice_id) if scenario else False

#Step 4: Speech to Text From 11labs
def transcribe_audio(audio_path: str, output_path: str, api_key: str) -> Optional[dict]:
    if not Path(audio_path).is_file():
        print(f"Audio file not found: {audio_path}")
        return None
    
    headers = {"xi-api-key": api_key}
    data = {"model_id": "scribe_v1"}
    try:
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers=headers,
                files={"file": audio_file},
                data=data
            )
            response.raise_for_status()
            transcription = response.json()
            with open(output_path, "w") as json_file:
                json.dump(transcription, json_file, indent=4)
            print(f"Transcription saved to {output_path}")
            return transcription
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

transcription = transcribe_audio(audio_path, json_path, api_key_11labs) if audio_success else None

#Step 5: Subtitles Creation
def create_ass_subtitles(transcription: dict, output_path: str):
    if not transcription:
        print("No transcription available for ASS creation.")
        return
    
    def seconds_to_ass_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02.2f}"
    
    ass_header = """[Script Info]
    Title: Modern Subtitles
    ScriptType: v4.00+

    [V4+ Styles]

    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Ubuntu,16,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,1,2,70,70,10,1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """
    ass_lines = []
    for word in transcription['words']:
        if word['type'] == 'word':
            start_time = seconds_to_ass_time(word['start'])
            end_time = seconds_to_ass_time(word['end'])
            text = word['text'].replace(",", "")
            duration = int((word['end'] - word['start']) * 100)
            ass_lines.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\k{duration}}}{text}")

    with open(output_path, "w", encoding='utf-8') as f:
        f.write(ass_header + "\n".join(ass_lines))
        print(f"ASS subtitles saved to {output_path}")

create_ass_subtitles(transcription, ass_path)

#Step 6: Final .mp4 video
def create_final_video(video_path: str, audio_path: str, ass_path: str, output_path: str):
    if not all([video_path, Path(audio_path).is_file(), Path(ass_path).is_file()]):
        print("Missing required files for final video.")
        return
    
    def get_duration(file_path: str) -> float:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    
    video_dur = get_duration(video_path)
    audio_dur = get_duration(audio_path)
    loops = int((audio_dur + video_dur - 0.001) / video_dur) - 1
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-stream_loop', str(loops),
        '-i', video_path,
        '-i', audio_path,
        '-filter_complex', '[0:v]subtitles=subtitles.ass:force_style=\'Alignment=2\'[v]',
        '-map', '[v]',
        '-map', '1:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', str(audio_dur),
        output_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Final video saved to {output_path}")
    else:
        print(f"Error during video processing: {result.stderr}")

output_video_path = "output_video_with_subs.mp4"
create_final_video(video_path, audio_path, ass_path, output_video_path)