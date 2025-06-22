#!/usr/bin/env python3
"""
Script to debug authentication and set up metrics UI
Uses the real database configuration from settings
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.auth import auth_manager
from app.db.session import db_manager
from app.models.user_model import User

def debug_auth_token():
    """Debug authentication token issues"""
    print("🔐 Debugging Authentication")
    print("-" * 40)
    
    session = db_manager.SessionLocal()
    
    try:
        # Get the superadmin user
        superadmin = session.query(User).filter(User.role_id == 1).first()
        
        if not superadmin:
            print("❌ No superadmin found!")
            return
            
        print(f"👑 Superadmin User: {superadmin.username}")
        print(f"📧 Email: {superadmin.email}")
        print(f"🆔 Role ID: {superadmin.role_id}")
        print(f"✅ Active: {superadmin.is_active}")
        
        # Create a test token
        print("\n🎫 Creating test token...")
        test_token = auth_manager.create_access_token(
            data={"sub": str(superadmin.user_id)}
        )
        print(f"Token created: {test_token[:50]}...")
        
        # Verify the token
        print("\n🔍 Verifying token...")
        try:
            payload = auth_manager.verify_token(test_token)
            print(f"✅ Token verified successfully")
            print(f"Payload: {payload}")
            
            # Get user from token
            user_id = payload.get("sub")
            if user_id:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    print(f"✅ User found from token: {user.username}")
                    print(f"   Role ID: {user.role_id}")
                else:
                    print("❌ User not found from token")
            
        except Exception as e:
            print(f"❌ Token verification failed: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

def setup_metrics_info():
    """Provide information about metrics setup"""
    print("\n📊 Metrics UI Setup")
    print("-" * 40)
    
    print("The /metrics endpoint provides Prometheus metrics.")
    print("To view metrics in a UI, you have several options:")
    print()
    print("1. 🐳 Quick Grafana Setup (Docker):")
    print("   docker run -d -p 3000:3000 grafana/grafana-oss")
    print("   Then go to: http://localhost:3000")
    print("   Login: admin/admin")
    print()
    print("2. 🔍 Prometheus + Grafana:")
    print("   - Set up Prometheus to scrape http://localhost:8000/metrics")
    print("   - Configure Grafana to use Prometheus as data source")
    print()
    print("3. 📱 Simple Metrics Viewer:")
    print("   - Visit: http://localhost:8000/metrics directly")
    print("   - Use browser extensions for better formatting")
    print()
    print("4. 🛠️ Add metrics dashboard to your app:")
    print("   - Create a new admin page that fetches /metrics")
    print("   - Parse and display key metrics in your UI")

def create_simple_metrics_endpoint():
    """Create a simple metrics viewer endpoint"""
    print("\n🔧 Creating Simple Metrics Viewer")
    print("-" * 40)
    
    metrics_router_code = '''
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import requests

metrics_router = APIRouter()

@metrics_router.get("/admin/metrics-viewer", response_class=HTMLResponse)
async def metrics_viewer(request: Request):
    """Simple metrics viewer page"""
    try:
        # Fetch metrics from the /metrics endpoint
        response = requests.get("http://localhost:8000/metrics")
        metrics_text = response.text
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Metrics Viewer</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                .metric {{ margin: 10px 0; padding: 10px; background: #f5f5f5; }}
                .refresh {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>📊 Application Metrics</h1>
            <div class="refresh">
                <button onclick="location.reload()">🔄 Refresh</button>
            </div>
            <pre>{metrics_text}</pre>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"<h1>Error loading metrics: {e}</h1>"
'''
    
    print("You can add this to your FastAPI app:")
    print(metrics_router_code)

if __name__ == "__main__":
    debug_auth_token()
    setup_metrics_info()
    create_simple_metrics_endpoint()
    
    print("\n" + "="*60)
    print("🎯 Next Steps:")
    print("1. Check if the authentication token is working correctly")
    print("2. Verify role-based access in the router endpoints")
    print("3. Set up metrics UI using one of the suggested methods")
    print("4. Test the access control with the corrected authentication") 