import sys
sys.path.append(r'c:\Users\bhrga\Downloads\content-automation-main\content-automation-main')
from drive_uploader import DriveUploader
import logging

logging.basicConfig(level=logging.ERROR)

def check():
    uploader = DriveUploader()
    service = uploader._get_service()
    folders = ['1euAsq1h5JyAOt88VfbBZzOetCESNqPdN', 'Poetry Test Folder']
    
    for f_spec in folders:
        try:
            fid = uploader.get_or_create_folder(f_spec)
            all_files = []
            page_token = None
            while True:
                res = service.files().list(
                    q=f"'{fid}' in parents and trashed = false", 
                    fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token
                ).execute()
                all_files.extend(res.get('files', []))
                page_token = res.get('nextPageToken')
                if not page_token:
                    break
            
            videos = [f for f in all_files if f['mimeType'] == 'video/mp4']
            meta = [f for f in all_files if f['mimeType'] == 'application/json']
            
            print(f"\n📁 FOLDER: {f_spec} (ID: {fid})")
            print(f"   Total items: {len(all_files)}")
            print(f"   Videos (.mp4): {len(videos)}")
            print(f"   Metadata (.json): {len(meta)}")
            if videos:
                print("   All videos:")
                for v in sorted(videos, key=lambda x: x['name']):
                    print(f"    - {v['name']}")
        except Exception as e:
            print(f"Error checking {f_spec}: {e}")

if __name__ == "__main__":
    check()
