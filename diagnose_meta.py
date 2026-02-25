"""
Meta AI Cookie Diagnostic Tool
================================

This script helps diagnose Meta AI connection issues and guides you through
updating cookies if needed.

Usage:
    python diagnose_meta.py
"""

import os
import sys

# Add metaai-api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'metaai-api'))

from metaai_api import MetaAI

def test_cookies():
    """Test if current cookies are valid."""
    
    print("🔍 Meta AI Cookie Diagnostic Tool")
    print("=" * 50)
    print()
    
    # Current cookies from generate_reel.py
    cookies = {
        "datr": "AP2NaQK7olTjm_TvBSXPqHhB",
        "abra_sess": "FqyV5szPn9YDFioYDjg3Vm5VN0J3c2pyb1FBFvb%2F75gNAA%3D%3D==",
        "ecto_1_sess": "36ba8935-2b8b-4f84-a08a-a6bc715dc5b4.v1%3AxGMSNaL_f8zDMDnDjb4ZnfXo-slIfe-XvQ2zAAhLqmDSTPUTdSzypQK3k5OX_IvXF48O1Mwd8HWbfPNY1J5bemG5oFbQuueRRUNZi_X9Hhyj5lNr5Z3r5kywzUhkBapJU_cQXjd8NloSMMhZft_0xmaVmYjuS1qs1JTAhARB5jPTgOopwoEtKyLJdRsKV-NA0FGSWsP-awwSztQ95e1c6t1Yuw7IKZ90L5YuloL3oJeRl_Qt615KP4nYGG4UakFERlTeUKlcDnQDsV9HP9nq8TGWDrXhU8uiSwXASDCPgLdZcj8MSenhHPmOSed0i8xPqfq1Z5g96pxzfqEfgivIXAGT4j6YxQ2KA4CNrNKv7rJ0M2H_qb7BtBnPUiUkvMkItgaidmixEEljTMkrADsDK9QKVpw3fvaXYeQGvgjhfpCUogugI-hy4jiiRAOYDNCdc84254id8UxUVWKqfpO480qoduVUkfTrwovMv8vUp4w06JfRNEoqD1HiDrm3%3AhNRxYHbVcmsG3aF_%3AnsWRU_UH8mQkg2J0nsDmog.QHdEll4bupl8SrOkGzCdkk3H0IGAeCFm3cMu3IcZ7Tg"
    }
    
    print("📋 Current Cookies:")
    for key, value in cookies.items():
        masked = value[:10] + "..." + value[-10:] if len(value) > 20 else value
        print(f"   {key}: {masked}")
    print()
    
    print("🔌 Testing connection to Meta AI...")
    try:
        ai = MetaAI(cookies=cookies)
        print("✅ MetaAI object created successfully")
        print()
        
        # Try a simple image generation first (faster than video)
        print("🎨 Testing with simple image generation...")
        response = ai.generate_image("a red apple on a table", num_images=1)
        
        if response.get("success") and response.get("image_urls"):
            print("✅ Image generation SUCCESSFUL!")
            print(f"   Generated {len(response['image_urls'])} image(s)")
            print()
            print("🎉 Cookies are VALID and working!")
            print()
            return True
        else:
            print("❌ Image generation FAILED")
            print(f"   Response: {response}")
            print()
            print("⚠️ Cookies may be expired or invalid")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("⚠️ Connection failed - cookies are likely invalid")
        print()
        return False

def print_cookie_update_guide():
    """Print instructions for updating cookies."""
    
    print("=" * 50)
    print("📖 HOW TO UPDATE META AI COOKIES")
    print("=" * 50)
    print()
    print("1. Open Chrome/Edge and go to: https://www.meta.ai/")
    print()
    print("2. Open Developer Tools (F12)")
    print()
    print("3. Go to: Application → Cookies → https://www.meta.ai")
    print()
    print("4. Copy these 3 cookies:")
    print("   • datr")
    print("   • abra_sess")
    print("   • ecto_1_sess")
    print()
    print("5. Update the cookies in these files:")
    print("   • generate_reel.py (line ~200)")
    print("   • test_meta_video.py (line ~50)")
    print("   • video.py (if using the old pipeline)")
    print()
    print("6. Format:")
    print('   cookies = {')
    print('       "datr": "YOUR_DATR_VALUE",')
    print('       "abra_sess": "YOUR_ABRA_SESS_VALUE",')
    print('       "ecto_1_sess": "YOUR_ECTO_1_SESS_VALUE"')
    print('   }')
    print()
    print("=" * 50)

def main():
    is_valid = test_cookies()
    
    if not is_valid:
        print_cookie_update_guide()
        print()
        print("💡 TIP: Cookies typically expire after 24-48 hours")
        print("   You'll need to refresh them periodically")
    else:
        print("✅ All systems operational!")
        print("   You can now use:")
        print("   • python test_meta_video.py --prompt 'your prompt' --style nostalgic_oil")
        print("   • python generate_reel.py --topic 'your topic' --style nostalgic_oil")

if __name__ == "__main__":
    main()
