import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def send_test_email():
    try:
        # Configuración del correo
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = GMAIL_USER   # te lo envías a ti mismo
        msg["Subject"] = "✅ Prueba exitosa de Gmail"

        body = "Hola Jonás, tu configuración de Gmail funciona correctamente."
        msg.attach(MIMEText(body, "plain"))

        # Conexión con Gmail
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        server.quit()

        print("✅ Correo enviado con éxito a", GMAIL_USER)

    except Exception as e:
        print("❌ Error al enviar correo:", e)


if __name__ == "__main__":
    send_test_email()
