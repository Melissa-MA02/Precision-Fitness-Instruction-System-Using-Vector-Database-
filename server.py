from flask import Flask, request, jsonify, render_template
import openai
import weaviate
import boto3
from moviepy.editor import VideoFileClip, concatenate_videoclips
import time
from requests.exceptions import ConnectionError
from langchain_community.llms import OpenAI

app = Flask(__name__)

# AWS Configuration please put your own aws_access keys and secret access keys
aws_access_key_id = '' 
aws_secret_access_key = ''
bucket_name = 'mybucketcapstonemel'

# OpenAI API key configuration please put your own open_api_access keys and secret access keys
openai_api_key = ""
openai.api_key = openai_api_key

# Weaviate client setup
client = weaviate.Client(
    url="https://melissa-al1pmgzg.weaviate.network",
    auth_client_secret=weaviate.auth.AuthApiKey(api_key="hOwgzYRuOB7zLnBGlrgC9csZ10PZ8WpylgiZ"),
    additional_headers={'X-OpenAI-Api-key': openai_api_key},
    timeout_config=(5, 15)
)

# Initialize the Langchain OpenAI LLM
llm = OpenAI(api_key=openai_api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_video', methods=['POST'])
def generate_video():
    user_profile = request.json
    concepts = generate_concepts(user_profile)
    video_urls = safe_query(client, concepts)
    if video_urls:
        download_and_stitch_videos(video_urls)
        # Assume that the video is saved locally in the server directory
        return jsonify({"videoUrl": "C:/Users/melis/Downloadsfinal_output.mp4"})
    else:
        return jsonify({"videoUrl": "No videos available"}), 404

def generate_concepts(user_profile):
    query_prompt = f"""
    Generate a list of exercise-related search concepts for a {user_profile['age']}-year-old {user_profile['gender']} who is at an {user_profile['level']} level of fitness. They focus on {', '.join(user_profile['focus_points'])}, enjoy {', '.join(user_profile['favorite_exercises'])}, dislike {', '.join(user_profile['least_favorite_exercises'])}, and need exercises that are suitable for {', '.join(user_profile['weakness'])}.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": query_prompt}],
        max_tokens=100,
        temperature=0.7
    )
    return response['choices'][0]['message']['content'].strip()

def safe_query(client, concepts, max_retries=5):
    video_urls = []
    retries = 0
    while retries < max_retries:
        try:
            response = client.query.get("Sciii", ["title", "description", "type", "bodyPart", "equipment", "level", "rest_time", "video_s3_url"]).with_near_text({"concepts": concepts}).with_limit(5).do()
            for item in response['data']['Get']['Sciii']:
                video_urls.append(item['video_s3_url'])
            return video_urls
        except ConnectionError:
            retries += 1
            time.sleep(2**retries)
            print(f"Retry {retries}/{max_retries}")
    return video_urls

def download_and_stitch_videos(urls):
    clips = []
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    for url in urls:
        file_name = url.split("/")[-1]
        local_file_path = f"C:/Users/melis/Downloads{file_name}"  # Update this path according to your OS and user
        try:
            s3.download_file(bucket_name, file_name, local_file_path)
            clip = VideoFileClip(local_file_path)
            clips.append(clip)
            print(f"Downloaded and loaded {file_name}")
        except Exception as e:
            print(f"Failed to download or load video {file_name}: {str(e)}")
    
    if clips:
        final_clip = concatenate_videoclips(clips, method='compose')
        final_output_path = "C:/Users/melis/Downloads/final_output.mp4"  # Specify your path here
        final_clip.write_videofile(final_output_path)
        print(f"All videos have been stitched together into {final_output_path}")
    else:
        print("No videos were downloaded or stitched.")


if __name__ == '__main__':
    app.run(debug=True)
