import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Alcance mínimo: solo lectura de archivos de Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def list_drive_files():
    try:
        # Autenticación con Service python drive_test.py

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)

        # Listar archivos dentro de la carpeta
        query = f"'{FOLDER_ID}' in parents"
        results = service.files().list(
            q=query, pageSize=10, fields="files(id, name)"
        ).execute()
        files = results.get("files", [])

        if not files:
            print("⚠️ No se encontraron archivos en la carpeta.")
        else:
            print("📂 Archivos en la carpeta de Drive:")
            for file in files:
                print(f"- {file['name']} ({file['id']})")

    except Exception as e:
        print("❌ Error al conectar con Google Drive:", e)


if __name__ == "__main__":
    list_drive_files()
