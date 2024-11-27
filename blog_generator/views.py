from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
#from pytube import YouTube
import yt_dlp
import os
import assemblyai as aai
from openai import OpenAI
from .models import BlogPost
import logging
logger = logging.getLogger(__name__)
import re


def clean_title(title):
    # Replace special characters with an underscore or remove them
    # You can adjust the regex pattern based on your needs
    return re.sub(r'[<>:"/\\|?*]', '_', title)  # Replace special characters


# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)


        # get yt title
        title = yt_title(yt_link)

        # get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': " Failed to get transcript"}, status=500)


        # use OpenAI to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': " Failed to generate blog article"}, status=500)

        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()  # Save is handled automatically by create() so, code work without this line

        # return blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    try:
        yt = yt_dlp.YoutubeDL()
        # Extract information without downloading
        info = yt.extract_info(link, download=False)  # Set download=True if you want to download the video
        title = info.get('title', 'Unknown Title')  # Default to 'Unknown Title' if title is not found
        #title = yt.title
        return title
    except Exception as e:
        logger.error(f"Error retrieving title: {e}")  # Use logging instead of print
        return "Error retrieving title"

def download_audio(link):
    try:
        # Set options for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',  # Get the best audio format
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),  # Save to MEDIA_ROOT with title
            'postprocessors': [{  # Convert to mp3 after download
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as yt:
            info = yt.extract_info(link, download=True)  # This will download the audio


        # Clean the title to remove special characters
        cleaned_title = clean_title(info['title'])

        
        # Construct the path of the downloaded file
        audio_file = os.path.join(settings.MEDIA_ROOT, f"{info['title']}.mp3")
        return audio_file
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")  # Use logging instead of print
        return "Error downloading audio"

'''def download_audio(link):
    yt = yt_dlp.YoutubeDL()
    # Extract video info
    info = yt.extract_info(link, download=False)
    # Get the audio stream URL
    audio_url = info['formats'][0]['url']
    #video = yt.streams.filter(only_audio=True).first()
    #audio download
    #out_file = yt.download(audio_url, output_path=settings.MEDIA_ROOT)
    out_file = yt.download(audio_url)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file 
'''

def get_transcription(link):
    audio_file = download_audio(link)
    if audio_file.startswith("Error"): ## Check if there was an error downloading audio
        return audio_file #return error
    aai.settings.api_key ="Your aai key"

    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file)
        return transcript.text
    except Exception as e:
        logger.error(f"Error getting transcription: {e}")  # Use logging instead of print
        return "Error transcribing audio"

    #OPENAI part

def generate_blog_from_transcription(transcription):
    client = OpenAI("Your Open AI key")  # Replace with your actual API key
    try:
        completion = client.chat.completions.create(
            model="gpt-4",  # Ensure you're using a valid model ID
            max_tokens=250,
            messages=[
                {"role": "user", "content": f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but don't make it look like a YouTube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"}
            ]
        )

        # Access the generated content correctly
        generated_content = completion.choices[0].message.content  # Correct way to access the content
        return generated_content

    except Exception as e:
        logger.error(f"Error generating_blog_from_transcription: {e}")  # Use logging instead of print
        return None  # Or handle the error as needed



def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    try:
        blog_article_detail = BlogPost.objects.get(id=pk)
        if request.user == blog_article_detail.user:
            return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
        else:
            return redirect('/')
    except BlogPost.DoesNotExist:
        return JsonResponse({'error': 'Blog post not found'}, status=404)

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})
        
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message':error_message})
        
    return render(request, 'signup.html')

def user_logout(request, pk=None):
    logout(request)
    return redirect('/')
