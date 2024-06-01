import os, time, warnings
from flask import Flask, request, send_file
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

load_dotenv()

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
thread = client.beta.threads.create()
twilio_account_sid = os.environ["TWILIO_ACCOUNT_SID"]
twilio_auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio_client = Client(twilio_account_sid, twilio_auth_token)

@app.route('/intro', methods=['POST'])
def intro():
    resp = VoiceResponse()
    gather = Gather(input='speech', action='/gather', speechTimeout='auto')
    client.beta.threads.messages.create(
        thread_id=thread.id, 
        role="assistant",
        content="Athletes Foot Savannah, how can I help you today?"
    )
    resp.play(synthesize_speech('Athletes Foot Savannah, how can I help you today'))
    resp.append(gather)
    
    return str(resp)

@app.route("/gather", methods=['POST'])
def gather():
    """Process the speech input from the caller."""
    user_input = request.values.get('SpeechResult')
    
    response_text = generate_response(user_input)
    audio_response_path = synthesize_speech(response_text)

    resp = VoiceResponse()
    resp.play(audio_response_path)

    gather = Gather(input='speech', action='/gather', speechTimeout='auto')
    resp.append(gather)
    
    return str(resp)

@app.route("/static/<filename>")
def serve_audio(filename):
    return send_file(f"static/{filename}")


def synthesize_speech(resp):
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    speech_file_path = Path(__file__).parent / "static/speech.mp3"
    response = client.audio.speech.create(
        model="tts-1",
        voice="echo",
        input=resp
    )
    response.stream_to_file(speech_file_path)
    
    return request.host_url + "static/speech.mp3"

def generate_response(text):
    client.beta.threads.messages.create(
        thread_id=thread.id, 
        role="user",
        content=text,
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=os.environ["ASSISTANT_ID"]
    )

    run_status = client.beta.threads.runs.retrieve(
        thread_id = thread.id,
        run_id = run.id
    )

    while run_status.status not in ["completed", "failed", "requires_action"]:
        run_status = client.beta.threads.runs.retrieve(
            thread_id = thread.id,
            run_id = run_status.id)
        time.sleep(0.5)
        print(run_status.status)
    
    response = client.beta.threads.messages.list(
        thread_id = thread.id).data[0].content[0].text.value
    print(response)

    return response

if __name__ == "__main__":
    app.run(port=8000, debug=True)