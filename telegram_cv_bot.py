#!/usr/bin/env python3
# telegram_cv_bot.py

import os
import io
import json
import logging
import mimetypes
from dotenv import load_dotenv
from email.message import EmailMessage
import smtplib
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# --- Cargar variables de entorno ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
DRIVE_SERVICE_ACCOUNT_JSON = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
BOT_OWNER_NAME = os.getenv("BOT_OWNER_NAME", "Usuario")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Estados de la conversación ---
COMPANY, VACANCY, EMAIL, SELECT_CV, CONFIRM_NEW = range(5)

# --- Configuración de Google Drive ---
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ✅ Cambio aquí: cargar credenciales desde variable de entorno (JSON string)
creds_info = json.loads(DRIVE_SERVICE_ACCOUNT_JSON)
creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

# --- Helpers para Google Drive ---
def list_files_in_folder(folder_id, page_size=20):
    q = f"'{folder_id}' in parents and trashed=false"
    res = drive_service.files().list(
        q=q, pageSize=page_size, fields="files(id,name,mimeType)"
    ).execute()
    return res.get("files", [])

def download_file_to_bytes(file_id):
    meta = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
    file_name = meta.get("name")
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fd=fh, request=request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return file_name, fh.read(), meta.get("mimeType")

# --- Helpers para Gmail ---
def build_email_message(
    from_addr, to_addr, subject, body_text, body_html=None,
    attachment_bytes=None, attachment_filename=None, attachment_mime=None
):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    if attachment_bytes and attachment_filename:
        maintype, subtype = (
            attachment_mime.split("/", 1) if attachment_mime else ("application", "octet-stream")
        )
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_filename,
        )
    return msg

def send_email_smtp(msg: EmailMessage):
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)

# --- Handlers de Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Hola {BOT_OWNER_NAME}! Soy tu bot para enviar CVs.\n\n"
        "✍️ Escribe el *nombre de la empresa* a la que quieres postularte:",
        parse_mode="Markdown",
    )
    return COMPANY

async def get_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["company"] = update.message.text.strip()
    await update.message.reply_text("💼 Ahora dime el *cargo/vacante* a la que aplicas:", parse_mode="Markdown")
    return VACANCY

async def get_vacancy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["vacancy"] = update.message.text.strip()
    await update.message.reply_text("📧 Escribe el correo del reclutador:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text.strip()

    files = list_files_in_folder(DRIVE_FOLDER_ID)
    if not files:
        await update.message.reply_text("❌ No encontré archivos en la carpeta de Drive.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f["name"], callback_data=f["id"])] for f in files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📂 Selecciona el CV que quieres enviar:", reply_markup=reply_markup)
    return SELECT_CV

async def select_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    file_id = query.data
    file_name, file_bytes, mime_type = download_file_to_bytes(file_id)

    company = context.user_data.get("company")
    vacancy = context.user_data.get("vacancy")
    to_email = context.user_data.get("email")

    subject = f"Postulación a {vacancy} en {company}"

    body_text = (
        f"Estimado reclutadores de {company},\n\n"
        f"Adjunto mi CV para aplicar al cargo {vacancy} en {company}.\n\n"
        f"Saludos cordiales,\n"
        f"Ing. Jonás Coronado Gómez\n"
        f"Cel: 3167977211 - 3002330395\n"
        f"Barranquilla, Atlántico"
    )

    # --- Mantener el formato HTML original ---
    body_html = f"""
    <html>
      <body>
        <p>Estimado reclutadores de <strong>{company}</strong>,</p>
        <p>
          Adjunto mi CV para aplicar al cargo 
          <b><i>{vacancy}</i></b> en <b><i>{company}</i></b>.
        </p>
        <br>
        <p>Saludos cordiales,</p>
        <p>
          <b>Ing. Jonás Coronado Gómez</b><br>
          Cel: 3167977211 - 3002330395<br>
          Barranquilla, Atlántico
        </p>
      </body>
    </html>
    """

    msg = build_email_message(
        GMAIL_USER, to_email, subject,
        body_text, body_html,
        attachment_bytes=file_bytes,
        attachment_filename=file_name,
        attachment_mime=mime_type
    )

    ok, error = send_email_smtp(msg)
    if ok:
        fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Registrar en el chat en un nuevo mensaje
        registro = (
            "✅ *Aplicación Exitosa:*\n\n"
            f"🏢 *Nombre de la Empresa:* {company}\n"
            f"💼 *Vacante:* {vacancy}\n"
            f"🕒 *Fecha y Hora de Aplicación:* {fecha_hora}\n"
            f"📎 *CV Enviado:* {file_name}"
        )
        await query.message.reply_text(registro, parse_mode="Markdown")

        # Preguntar si desea nuevo envío
        keyboard = [
            [
                InlineKeyboardButton("✅ Sí", callback_data="new_yes"),
                InlineKeyboardButton("❌ No", callback_data="new_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("¿Deseas realizar un nuevo envío?", reply_markup=reply_markup)

        return CONFIRM_NEW
    else:
        await query.edit_message_text(f"❌ Error al enviar: {error}")
        return ConversationHandler.END

async def confirm_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "new_yes":
        await query.edit_message_text("🔄 Perfecto, vamos a realizar un nuevo envío.\n\n✍️ Escribe el *nombre de la empresa*:", parse_mode="Markdown")
        return COMPANY
    else:
        await query.edit_message_text("✅ Proceso finalizado. Cuando quieras enviar otro CV, usa /start.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Proceso cancelado.")
    return ConversationHandler.END

# --- Main ---
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ No se encontró TELEGRAM_TOKEN en el archivo .env")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_company)],
            VACANCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vacancy)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            SELECT_CV: [CallbackQueryHandler(select_cv)],
            CONFIRM_NEW: [CallbackQueryHandler(confirm_new)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    print("🤖 Bot corriendo... escribe /start en tu Telegram para probarlo.")
    application.run_polling()

if __name__ == "__main__":
    main()
