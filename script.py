import os
import time
import shutil
import whisper
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ssl
import certifi

# Ruta donde WhatsApp guarda los audios (ajusta si es necesario)
WHATSAPP_AUDIO_DIR = os.path.expanduser(
    "/Users/jeisson/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media"
)
OUTPUT_DIR = os.path.expanduser("~/WhatsAppTranscripts")  # Carpeta donde se guardarán las transcripciones

# Asegurar que la carpeta de salida exista
os.makedirs(OUTPUT_DIR, exist_ok=True)

ssl._create_default_https_context = ssl._create_unverified_context

# Cargar modelo de Whisper
model = whisper.load_model("small")  # Cambia a "medium" o "large" si necesitas mejor precisión


def convert_audio_to_wav(input_file, output_file):
    """Convierte el audio a WAV para Whisper usando ffmpeg."""
    try:
        subprocess.run(["ffmpeg", "-i", input_file, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", output_file, "-y"],
                       check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir audio: {e}")
        return False


def transcribe_audio(file_path):
    """Transcribe un archivo de audio y guarda el texto."""
    wav_path = file_path.replace(".ogg", ".wav")
    wav_path = wav_path.replace(".opus", ".wav")
    wav_path = wav_path.replace(".m4a", ".wav")

    if convert_audio_to_wav(file_path, wav_path):
        result = model.transcribe(wav_path, fp16=False)
        print(result)
        transcript = result["text"]
        os.remove(wav_path)  # Borra el archivo convertido
        return transcript
    return None


class WhatsAppAudioHandler(FileSystemEventHandler):
    """Detecta nuevos archivos de audio y los transcribe automáticamente."""

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if file_path.endswith(".ogg") or file_path.endswith(".m4a") or file_path.endswith(".opus"):
            print(f"Nuevo audio detectado: {file_path}")
            time.sleep(1)  # Esperar para asegurar que el archivo esté completamente escrito

            transcript = transcribe_audio(file_path)
            if transcript:
                output_file = os.path.join(OUTPUT_DIR, os.path.basename(file_path) + ".txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(transcript)
                print(f"✅ Transcripción guardada: {output_file}")

                # (Opcional) Mover archivo original a una subcarpeta de procesados
                processed_folder = os.path.join(WHATSAPP_AUDIO_DIR, "Processed")
                os.makedirs(processed_folder, exist_ok=True)
                shutil.move(file_path, os.path.join(processed_folder, os.path.basename(file_path)))
                print(f"📂 Archivo movido a {processed_folder}")


if __name__ == "__main__":
    observer = Observer()
    event_handler = WhatsAppAudioHandler()
    observer.schedule(event_handler, WHATSAPP_AUDIO_DIR, recursive=True)

    print("🎙️ Servicio de transcripción de WhatsApp iniciado...")
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()