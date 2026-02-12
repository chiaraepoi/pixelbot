import os
import csv
import logging
import configparser
import shutil
from tempfile import NamedTemporaryFile

from mastodon import Mastodon
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

# =========================
# FILE & CONFIG
# =========================

CONFIG_FILE = "config.ini"
QUEUE_FILE = "queue.csv"
LOG_FILE = "bot.log"
PUBLISHED_FOLDER = "./PUBLISHED"

# Creazione cartella pubblicati
os.makedirs(PUBLISHED_FOLDER, exist_ok=True)

# =========================
# LOGGING
# =========================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# CONFIG
# =========================

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

API_BASE_URL = config["Pixelfed"]["api_base_url"]
ACCESS_TOKEN = config["Pixelfed"]["access_token"]

AUTO_ALT = config.getboolean("Bot", "auto_alt", fallback=True)
ALT_PREFIX = config["Bot"].get("alt_prefix", "").strip()
MAX_ALT_LENGTH = config["Bot"].getint("max_alt_length", fallback=300)

# =========================
# PIXELFED CLIENT
# =========================

mastodon = Mastodon(
    access_token=ACCESS_TOKEN,
    api_base_url=API_BASE_URL
)

# =========================
# BLIP MODEL
# =========================

device = "cuda" if torch.cuda.is_available() else "cpu"
processor = None
model = None

def load_blip():
    global processor, model
    if processor is None or model is None:
        logging.info("Caricamento modello BLIP per ALT text...")
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            ignore_mismatched_sizes=True
        ).to(device)
        model.eval()

def generate_alt_text(image_path):
    load_blip()

    image = Image.open(image_path).convert("RGB")
    inputs = processor(image, return_tensors="pt").to(device)

    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=50)

    caption = processor.decode(output[0], skip_special_tokens=True)
    if not caption:
        raise RuntimeError("ALT text generato vuoto")

    caption = caption.strip().rstrip(".").capitalize()
    if ALT_PREFIX:
        caption = f"{ALT_PREFIX} {caption}"

    return caption[:MAX_ALT_LENGTH]

# =========================
# QUEUE HANDLING
# =========================

def read_queue():
    if not os.path.exists(QUEUE_FILE):
        logging.warning("queue.csv non trovato.")
        return None, []

    with open(QUEUE_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        logging.info("Queue vuota.")
        return None, []

    return rows[0], rows

def write_queue(rows):
    temp = NamedTemporaryFile(mode="w", delete=False, newline="", encoding="utf-8")
    with temp:
        writer = csv.writer(temp, delimiter=";")
        writer.writerows(rows)
    shutil.move(temp.name, QUEUE_FILE)

# =========================
# POSTING
# =========================

def post_to_pixelfed(image_path, caption, alt_text=None, sensitive=False, spoiler_text=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Immagine non trovata: {image_path}")

    media = mastodon.media_post(
        image_path,
        description=alt_text if alt_text else None
    )

    mastodon.status_post(
        status=caption,
        media_ids=[media["id"]],
        sensitive=sensitive,
        spoiler_text=spoiler_text
    )

# =========================
# MAIN
# =========================

def main():
    first_row, all_rows = read_queue()
    if not first_row:
        return

    if len(first_row) < 2:
        logging.error("Riga CSV non valida (minimo 2 campi richiesti).")
        return

    # Lettura campi CSV
    image_path = first_row[0].strip()
    caption = first_row[1].strip()
    alt_text = first_row[2].strip() if len(first_row) >= 3 else ""
    nsfw_flag = first_row[3].strip().lower() if len(first_row) >= 4 else ""
    cw_text = first_row[4].strip() if len(first_row) >= 5 else ""

    # Determinazione NSFW e CW
    sensitive = nsfw_flag in ["1", "true", "yes"]
    spoiler_text = cw_text if cw_text else None

    try:
        # Generazione ALT se mancante
        if not alt_text and AUTO_ALT:
            alt_text = generate_alt_text(image_path)
            logging.info(f"ALT generato automaticamente: [{alt_text}]")

        # Pubblicazione su Pixelfed
        post_to_pixelfed(
            image_path,
            caption,
            alt_text,
            sensitive=sensitive,
            spoiler_text=spoiler_text
        )

        # Rimuove la prima riga dal CSV
        write_queue(all_rows[1:])

        # Spostamento immagine pubblicata
        try:
            dest_path = os.path.join(PUBLISHED_FOLDER, os.path.basename(image_path))
            shutil.move(image_path, dest_path)
            logging.info(f"Immagine spostata in {PUBLISHED_FOLDER}: {image_path}")
        except Exception as e:
            logging.error(f"Errore nello spostamento dell'immagine: {e}")

        logging.info(f"Pubblicato con successo: {image_path}")

    except Exception as e:
        logging.error(f"Errore durante la pubblicazione: {e}")

if __name__ == "__main__":
    main()
