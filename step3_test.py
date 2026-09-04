from uri_core.services.drive_service import DriveService

def test_drive():
    print("Testing Google Drive Connection...")
    drive = DriveService()
    result = drive.list_recent_files()
    
    if result.get("success"):
        print("\nSUCCESS! URI can see your Google Drive. Recent files:")
        for file in result.get("files", []):
            print(f"- {file['name']} ({file['mimeType']})")
    else:
        print(f"\nFAILED: {result.get('reason')}")

if __name__ == "__main__":
    test_drive()
