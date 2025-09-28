import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Carpeta local donde se guardarán los CVs
LOCAL_FOLDER = "CVs"


def download_file(file_id, file_name):
    try:
        # Crear carpeta local si no existe
        if not os.path.exists(LOCAL_FOLDER):
            os.makedirs(LOCAL_FOLDER)

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)

        # Descargar contenido
        request = service.files().get_media(fileId=file_id)

        from googleapiclient.http import MediaIoBaseDownload
        import io

        local_path = os.path.join(LOCAL_FOLDER, file_name)
        fh = io.FileIO(local_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"⬇️  Descargando {file_name}: {int(status.progress() * 100)}%")

        print(f"✅ Archivo descargado en {local_path}")

    except Exception as e:
        print("❌ Error al descargar archivo:", e)


def list_and_choose_file():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)

        query = f"'{FOLDER_ID}' in parents"
        results = service.files().list(
            q=query, pageSize=10, fields="files(id, name)"
        ).execute()
        files = results.get("files", [])

        if not files:
            print("⚠️ No se encontraron archivos en la carpeta.")
            return

        print("📂 Archivos disponibles:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file['name']} ({file['id']})")

        # Selección del usuario
        choice = int(input("👉 Escribe el número del archivo que quieres descargar: "))
        selected = files[choice - 1]

        download_file(selected["id"], selected["name"])

    except Exception as e:
        print("❌ Error al listar archivos:", e)


if __name__ == "__main__":
    list_and_choose_file()
