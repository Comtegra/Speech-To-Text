import streamlit as st
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
import numpy as np
from pydub import AudioSegment
from st_audiorec import st_audiorec
from langdetect import detect
from audiorecorder import audiorecorder

st.set_page_config(page_title="Speech-To-Text", layout="wide", page_icon="./media/favicon.ico")

def timestamped_chunks(chunks):
    """Format and display timestamped chunks."""
    time_offset = 0

    for i, chunk in enumerate(chunks):
        # If start_time is 0, add 30 seconds to the next timestamp, becauase Whisper is chunking the audio in 30 second intervals.
        if i > 0:
            if chunk["timestamp"][0] == 0:
                time_offset += 30

        start_time = chunk["timestamp"][0] + (time_offset)
        end_time = chunk["timestamp"][1] + (time_offset)
   
        st.markdown(f"**[{format_time(start_time)} - {format_time(end_time)}]** {chunk['text']}")


def format_time(total_seconds):
    """Convert seconds to HH:MM:SS format."""
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def cut_audio(file, start_seconds, end_seconds):
    """Cut an audio file to a specific time range."""
    output = "tmp.wav"

    sound = AudioSegment.from_file(file)

    start_time = start_seconds * 1000
    end_time = end_seconds * 1000

    new_sound = sound[start_time:end_time]
    new_sound.export(output, format="wav")

    return output



st.title("🎙️ Speech-To-Text Transcription (Capable of Recognizing 99 Languages)")
st.write("Upload an audio file or record audio and let AI do the magic!")

#Sidebar
with st.sidebar:
    st.image("./media/comtegra_logo.png")
    st.header("Model configuration")
    model_id = st.selectbox("Choose a model:", ["openai/whisper-large-v3", "openai/whisper-large-v3-turbo"])
    num_beams = st.slider("Number of beams", min_value=1, max_value=10, value=5)
    st.caption("Evaluates multiple patterns of token connections and selects the best text. Smaller beam sizes reduce the number of decoder inference batches, resulting in faster processing.")
    condition_on_prev_tokens = st.checkbox("Condition on previous tokens")
    st.caption("Determines if the model should use previous words to help predict the next ones.")
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.6, step=0.01)
    st.caption("Controls the randomness of the output. Lower values make the output more deterministic, while higher values make it more creative.")
    st.subheader("About")
    st.write("Tool that transforms your voice into written text, effortlessly and accurately. Whether you're delivering a keynote, conducting an interview, or simply capturing ideas on the fly, listens, understands, and transcribes with incredible speed. But that's not all - it goes beyond borders. It let's you quickly translate your speech into multiple languages, breaking down communication barriers like never before. It's not just Speech-To-Text; it's speech to the world. Speak. Translate. Connect")
    st.write("Made with ❤️ by [Comtegra S.A.](https://cgc.comtegra.cloud)")
    st.subheader("Wsparcie")
    st.caption("Jeśli masz jakiekolwiek pytania, zapraszamy do kontaktu")
    st.write("[ai@comtegra.pl](mailto:ai@comtegra.pl)")


voice_recording = st.selectbox("Do you want to upload a file or record audio?", ["Upload a file", "Record audio"])

if voice_recording == "Record audio":
    st.header("Audio Recorder")
    audio = audiorecorder(start_prompt="", stop_prompt="", pause_prompt="", show_visualizer="True", key=None)
    st.caption("Press the microphone button to start recording. You can pause, resume and stop recording. When you're done, press the save button.")

    if len(audio) > 0:
        # To play audio in frontend:
        st.audio(audio.export().read())  
    uploaded_file = audio.export().read()
else:
    # Choose your file
    uploaded_file = st.file_uploader("Choose a file", type=["mp3", "wav", "ogg"])
    if uploaded_file:
        st.audio(uploaded_file)
        cut_audio_checkbox = st.checkbox("Cut audio to specific time range")
        if cut_audio_checkbox:
            start_time = st.number_input("Start time (seconds)", min_value=0, value=0)
            end_time = st.number_input("End time (seconds)", min_value=0, value=0)
            if end_time:
                if start_time < end_time:
                    uploaded_file = cut_audio(uploaded_file, start_time, end_time)
                    st.audio(uploaded_file)
                    st.caption("Audio cut to the selected time range. Try not to cut the audio in the middle of a word.")
                else:
                    st.warning("Start time must be less than end time")
            else:
                st.warning("Please enter start and end time")

priority_languages = "['default', 'polish', 'english']"
language_list = "['chinese', 'german', 'spanish', 'russian', 'korean', 'french', 'japanese', 'portuguese', 'turkish', 'catalan', 'dutch', 'arabic', 'swedish', 'italian', 'indonesian', 'hindi', 'finnish', 'vietnamese', 'hebrew', 'ukrainian', 'greek', 'malay', 'czech', 'romanian', 'danish', 'hungarian', 'tamil', 'norwegian', 'thai', 'urdu', 'croatian', 'bulgarian', 'lithuanian', 'latin', 'maori', 'malayalam', 'welsh', 'slovak', 'telugu', 'persian', 'latvian', 'bengali', 'serbian', 'azerbaijani', 'slovenian', 'kannada', 'estonian', 'macedonian', 'breton', 'basque', 'icelandic', 'armenian', 'nepali', 'mongolian', 'bosnian', 'kazakh', 'albanian', 'swahili', 'galician', 'marathi', 'punjabi', 'sinhala', 'khmer', 'shona', 'yoruba', 'somali', 'afrikaans', 'occitan', 'georgian', 'belarusian', 'tajik', 'sindhi', 'gujarati', 'amharic', 'yiddish', 'lao', 'uzbek', 'faroese', 'haitian creole', 'pashto', 'turkmen', 'nynorsk', 'maltese', 'sanskrit', 'luxembourgish', 'myanmar', 'tibetan', 'tagalog', 'malagasy', 'assamese', 'tatar', 'hawaiian', 'lingala', 'hausa', 'bashkir', 'javanese', 'sundanese', 'cantonese', 'burmese', 'valencian', 'flemish', 'haitian', 'letzeburgesch', 'pushto', 'panjabi', 'moldavian', 'moldovan', 'sinhalese', 'castilian', 'mandarin']"

# Parse the language_list string into a list
languages = eval(language_list)

# Sort the languages alphabetically
languages.sort()

final_languages = eval(priority_languages) + languages

# Create the selectbox with the parsed languages
st.header("Transcription settings")
audio_language = st.selectbox("Choose audio language: ", final_languages, index=final_languages.index('default'))
st.caption("Whisper predicts the language of the source audio automatically. If the source audio language is known a-priori, it can be passed as an argument to the pipeline to avoid misprediction. If not please leave default.")
translate_to_english = None
if model_id == "openai/whisper-large-v3":
    translate = st.checkbox("Translate to English")
    if translate:
        translate_to_english = True
timestamp_options = ["No timestamps", "Timestamps"]
timestamp_choice = st.selectbox("Timestamp options:", timestamp_options, index=0)

if timestamp_choice == "Timestamps":
    timestamps_status = True
else:
    timestamps_status = False
    


device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)
model.to(device)

processor = AutoProcessor.from_pretrained(model_id)

pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
)


generate_kwargs = {
    "num_beams": num_beams,
    "condition_on_prev_tokens": condition_on_prev_tokens,
    "temperature": temperature,
}

if translate_to_english == True:
    generate_kwargs["task"] = "translate"
    if audio_language != "default":
        generate_kwargs["language"] = audio_language
else:
    if audio_language != "default":
        generate_kwargs["language"] = audio_language


with st.spinner("Processing file..."):
    if st.button("Transcribe"):
        if uploaded_file is None:
            st.warning("Please upload a file or record audio")
        else:
            try:
                if voice_recording == "Record audio":
                    file = uploaded_file
                elif cut_audio_checkbox:
                    file = cut_audio(uploaded_file, start_time, end_time)
                else:
                    file = uploaded_file.read()
                if timestamp_choice != "No timestamps":
                    result = pipe(file, generate_kwargs=generate_kwargs, return_timestamps=timestamps_status)
                    st.header(f"Transcribed text in {detect(result['text'])}: ")
                    st.write(timestamped_chunks(result["chunks"]))
                else:
                    result = pipe(file, generate_kwargs=generate_kwargs)
                    st.header(f"Transcribed text in {detect(result['text'])}: ")
                    st.write(result["text"])

                # Write text to a file
                if timestamp_choice != "No timestamps":
                    f = open("translated_text.txt", "w")
                    for chunk in result["chunks"]:
                        start_time = format_time(chunk["timestamp"][0])
                        end_time = format_time(chunk["timestamp"][1])
                        f.write(f"**[{start_time} - {end_time}]** {chunk['text']}\n")
                    f.close()
                else:
                    f = open("translated_text.txt", "w")
                    f.write(result["text"])
                    f.close()

            except Exception as e:
                st.error(f"An error occurred during transcription: {str(e)}")

            # Display word count
            word_count = len(result["text"].split())
            st.info(f"Word count: {word_count}")

            # Download the file
            with open("translated_text.txt", "rb") as file:
                if translate_to_english == True:
                    st.download_button(label="Download translated text", data=file, file_name="translated_text.txt", mime="text/plain")
                else:
                    st.download_button(label="Download transcribed text", data=file, file_name="translated_text.txt", mime="text/plain")
