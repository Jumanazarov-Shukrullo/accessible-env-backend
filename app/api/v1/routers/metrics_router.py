from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
import requests
from app.core.auth import get_current_user
from app.core.constants import RoleID
from app.models.user_model import User

metrics_router = APIRouter(prefix="/admin", tags=["Metrics"])

@metrics_router.get("/metrics-viewer", response_class=HTMLResponse)
async def metrics_viewer(current_user: User = Depends(get_current_user)):
    """Simple metrics viewer page - only for admins and superadmins"""
    
    # Check if user has admin or superadmin role
    if current_user.role_id not in [RoleID.ADMIN.value, RoleID.SUPERADMIN.value]:
        raise HTTPException(403, "Only admins and superadmins can view metrics")
    
    try:
        # Fetch metrics from the /metrics endpoint
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        metrics_text = response.text
        
        # Parse some key metrics for display
        lines = metrics_text.split('\n')
        parsed_metrics = []
        
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            if ' ' in line:
                metric_name, value = line.split(' ', 1)
                try:
                    float_value = float(value)
                    parsed_metrics.append((metric_name, float_value))
                except ValueError:
                    parsed_metrics.append((metric_name, value))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>📊 Metrics Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0; padding: 20px; background: #f8fafc;
                }}
                .header {{ 
                    background: white; padding: 20px; border-radius: 8px; 
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;
                }}
                .metrics-grid {{ 
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px; margin-bottom: 20px;
                }}
                .metric-card {{ 
                    background: white; padding: 20px; border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .metric-name {{ font-weight: 600; color: #374151; margin-bottom: 8px; }}
                .metric-value {{ font-size: 24px; font-weight: 700; color: #059669; }}
                .refresh-btn {{ 
                    background: #3b82f6; color: white; border: none; padding: 10px 20px;
                    border-radius: 6px; cursor: pointer; font-weight: 500;
                }}
                .refresh-btn:hover {{ background: #2563eb; }}
                .raw-metrics {{ 
                    background: white; padding: 20px; border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-top: 20px;
                }}
                .raw-metrics pre {{ 
                    background: #f9fafb; padding: 15px; border-radius: 6px;
                    overflow-x: auto; font-size: 12px; margin: 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Application Metrics Dashboard</h1>
                <p>Welcome, {current_user.username}! Last updated: <span id="timestamp"></span></p>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Metrics</button>
            </div>
            
            <div class="metrics-grid">
        """
        
        # Add key metrics cards
        key_metrics = parsed_metrics[:12]  # Show first 12 metrics
        for metric_name, value in key_metrics:
            # Clean up metric name for display
            display_name = metric_name.replace('_', ' ').title()
            if isinstance(value, float):
                display_value = f"{value:.2f}" if value < 1000 else f"{value:,.0f}"
            else:
                display_value = str(value)
                
            html += f"""
                <div class="metric-card">
                    <div class="metric-name">{display_name}</div>
                    <div class="metric-value">{display_value}</div>
                </div>
            """
        
        html += f"""
            </div>
            
            <div class="raw-metrics">
                <h3>📋 Raw Metrics Data</h3>
                <pre>{metrics_text}</pre>
            </div>
            
            <script>
                document.getElementById('timestamp').textContent = new Date().toLocaleString();
                
                // Auto-refresh every 30 seconds
                setTimeout(() => location.reload(), 30000);
            </script>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Metrics Error</title></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>❌ Error Loading Metrics</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <p>Make sure the metrics endpoint is available at <code>/metrics</code></p>
            <button onclick="location.reload()">🔄 Try Again</button>
        </body>
        </html>
        """
