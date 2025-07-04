import streamlit as st
import openai
import weaviate
import time
import boto3
from moviepy.editor import VideoFileClip, concatenate_videoclips
from requests.exceptions import ConnectionError
from langchain_community.llms import OpenAI

#all keys should be your own
# AWS Configuration
aws_access_key_id = ''
aws_secret_access_key = ''
bucket_name = 'mybucketcapstonemel'

# OpenAI API key configuration
openai_api_key = ""
openai.api_key = openai_api_key

# Weaviate client setup
client = weaviate.Client(
    url="https://capstone20bce2543-jxnrz4sa.weaviate.network",
    auth_client_secret=weaviate.auth.AuthApiKey(api_key="LE9JY76cgiiSgNBC451tt7lZCXdCF2DaalNd"),
    additional_headers={'X-OpenAI-Api-key': openai_api_key},
    timeout_config=(5, 15)
)

# Initialize the Langchain OpenAI LLM
llm = OpenAI(api_key=openai_api_key)

# Define the Streamlit app
def streamlit_app():
    st.title('Exercise Video Generator')

    # Input fields
    age = st.number_input('Age', min_value=0, max_value=100, value=25, step=1)
    gender = st.selectbox('Gender', ('male', 'female', 'other'))
    level = st.selectbox('Fitness Level', ('beginner', 'intermediate', 'advanced'))
    focus_points = st.multiselect('Focus Points', ['chest', 'arms', 'legs', 'back', 'core'])
    favorite_exercises = st.multiselect('Favorite Exercises', ['walking', 'yoga', 'swimming', 'cycling', 'weightlifting', 'squats'])
    least_favorite_exercises = st.multiselect('Least Favorite Exercises', ['running', 'squats', 'weight lifting', 'planks'])
    weaknesses = st.multiselect('Physical Weaknesses', ['knee pain', 'back pain', 'none'])

    if st.button('Generate Videos'):
        user_profile = {
            "age": age,
            "gender": gender,
            "level": level,
            "focus_points": focus_points,
            "favorite_exercises": favorite_exercises,
            "least_favorite_exercises": least_favorite_exercises,
            "weakness": weaknesses
        }

        concepts = generate_concepts(user_profile)
        st.write("Generated Concepts:\n", concepts)

        # Query the Weaviate client and print the video URLs
        video_urls = safe_query(client, concepts)
        st.write("Video URLs:", video_urls)

        # Download and stitch videos if available
        if video_urls:
            download_and_stitch_videos(video_urls)
        else:
            st.write("No video URLs available to download and stitch.")

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
        try:
            s3.download_file(bucket_name, file_name, file_name)
            clip = VideoFileClip(file_name)
            clips.append(clip)
            print(f"Downloaded and loaded {file_name}")
        except Exception as e:
            print(f"Failed to download or load video {file_name}: {str(e)}")
    
    if clips:
        # Use 'compose' method to handle clips with different sizes or aspect ratios
        final_clip = concatenate_videoclips(clips, method='compose')
        final_clip.write_videofile("final_output.mp4")
        print("All videos have been stitched together into 'final_output.mp4'")
    else:
        print("No videos were downloaded or stitched.")

if __name__ == "__main__":
    streamlit_app()
