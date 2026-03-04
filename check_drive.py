from drive_uploader import DriveUploader
import logging

logging.basicConfig(level=logging.INFO)

def check_folders():
    uploader = DriveUploader()
    service = uploader._get_service()
    
    folders = ["1euAsq1h5JyAOt88VfbBZzOetCESNqPdN", "Poetry Test Folder"]
    
    for folder_spec in folders:
        print(f"\n--- Checking Folder: {folder_spec} ---")
        try:
            folder_id = uploader.get_or_create_folder(folder_spec)
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()
            files = results.get('files', [])
            print(f"Total files found: {len(files)}")
            for f in files[:5]:
                print(f" - {f['name']} ({f['id']})")
            if len(files) > 5:
                print("   ...")
        except Exception as e:
            print(f"Error checking {folder_spec}: {e}")

if __name__ == "__main__":
    check_folders()
