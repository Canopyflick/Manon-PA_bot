#!/usr/bin/env python3
"""
Test script to verify Ben ID configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.environment_vars import ENV_VARS

def test_ben_id_config():
    """Test if Ben ID is configured correctly"""
    print("=== BEN ID CONFIGURATION TEST ===")
    print(f"ENV_MODE: {getattr(ENV_VARS, 'ENV_MODE', 'NOT SET')}")
    print(f"BEN_ID: {getattr(ENV_VARS, 'BEN_ID', 'NOT SET')}")
    print(f"APPROVED_USER_IDS: {getattr(ENV_VARS, 'APPROVED_USER_IDS', 'NOT SET')}")
    
    expected_ben_id = 1875436366
    
    if hasattr(ENV_VARS, 'BEN_ID'):
        if ENV_VARS.BEN_ID == expected_ben_id:
            print(f"✅ BEN_ID is correctly set to {expected_ben_id}")
        else:
            print(f"❌ BEN_ID is set to {ENV_VARS.BEN_ID}, expected {expected_ben_id}")
    else:
        print("❌ BEN_ID is not set in environment variables")
    
    if hasattr(ENV_VARS, 'APPROVED_USER_IDS'):
        if expected_ben_id in ENV_VARS.APPROVED_USER_IDS:
            print(f"✅ {expected_ben_id} is in APPROVED_USER_IDS")
        else:
            print(f"⚠️  {expected_ben_id} is NOT in APPROVED_USER_IDS: {ENV_VARS.APPROVED_USER_IDS}")
            print("   This means the help command will work via BEN_ID but other security checks might fail")
    else:
        print("❌ APPROVED_USER_IDS is not set")
    
    # Test the helper function
    class MockUpdate:
        class EffectiveUser:
            def __init__(self, user_id):
                self.id = user_id
        
        def __init__(self, user_id):
            self.effective_user = self.EffectiveUser(user_id)
    
    # Import and test the function
    from features.help.command import is_user_ben
    
    print("\n=== FUNCTION TEST ===")
    test_update = MockUpdate(expected_ben_id)
    result = is_user_ben(test_update)
    print(f"is_user_ben({expected_ben_id}) returns: {result}")
    
    if result:
        print("✅ The help command should work correctly for Ben!")
    else:
        print("❌ The help command will still show the shy message to Ben")
        print("\n💡 SOLUTION:")
        print("Add to your .env file:")
        print(f"BEN_ID={expected_ben_id}")
        print(f"APPROVED_USER_IDS={expected_ben_id}")
        print("(or add to existing APPROVED_USER_IDS list)")


if __name__ == "__main__":
    test_ben_id_config()