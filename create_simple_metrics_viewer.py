#!/usr/bin/env python3
"""
Add a simple metrics viewer to the existing FastAPI app
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def create_simple_metrics_viewer():
    """Create a simple metrics viewer that can be added to main.py"""
    
    viewer_code = '''
# Add this to your main.py file after the existing routes

from fastapi.responses import HTMLResponse
import requests

@app.get("/admin/metrics-dashboard", response_class=HTMLResponse)
async def metrics_dashboard():
    """Simple metrics viewer - no authentication needed for demo"""
    try:
        # Fetch metrics from the existing /metrics endpoint
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        metrics_text = response.text
        
        # Parse key metrics
        lines = metrics_text.split('\\n')
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
                    margin: 0; padding: 20px; background: #f8fafc; color: #1a202c;
                }}
                .header {{ 
                    background: white; padding: 30px; border-radius: 12px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px;
                    text-align: center;
                }}
                .header h1 {{ margin: 0; color: #2d3748; font-size: 2.5rem; }}
                .header p {{ margin: 10px 0 0 0; color: #718096; }}
                .metrics-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                    gap: 20px; margin-bottom: 30px;
                }}
                .metric-card {{ 
                    background: white; padding: 25px; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    border-left: 4px solid #4299e1;
                    transition: transform 0.2s;
                }}
                .metric-card:hover {{ transform: translateY(-2px); }}
                .metric-name {{ 
                    font-weight: 600; color: #4a5568; margin-bottom: 12px; 
                    font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px;
                }}
                .metric-value {{ 
                    font-size: 2rem; font-weight: 700; color: #2d3748;
                    font-family: 'SF Mono', Monaco, monospace;
                }}
                .controls {{ 
                    background: white; padding: 20px; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px;
                    text-align: center;
                }}
                .refresh-btn {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; border: none; padding: 12px 24px;
                    border-radius: 8px; cursor: pointer; font-weight: 600;
                    margin: 0 10px; transition: all 0.3s;
                }}
                .refresh-btn:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
                .raw-metrics {{ 
                    background: white; padding: 25px; border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .raw-metrics h3 {{ color: #2d3748; margin-top: 0; }}
                .raw-metrics pre {{ 
                    background: #1a202c; color: #e2e8f0; padding: 20px; 
                    border-radius: 8px; overflow-x: auto; font-size: 13px; 
                    margin: 0; line-height: 1.5;
                }}
                .status-indicator {{
                    display: inline-block; width: 12px; height: 12px;
                    background: #48bb78; border-radius: 50%;
                    margin-right: 8px; animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0.5; }}
                    100% {{ opacity: 1; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Application Metrics</h1>
                <p><span class="status-indicator"></span>Live monitoring dashboard</p>
                <p><strong>Last Updated:</strong> <span id="timestamp"></span></p>
            </div>
            
            <div class="controls">
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Now</button>
                <button class="refresh-btn" onclick="window.open('/metrics', '_blank')">📋 Raw Metrics</button>
                <button class="refresh-btn" onclick="toggleAutoRefresh()">⏱️ <span id="auto-status">Auto: ON</span></button>
            </div>
            
            <div class="metrics-grid">
        """
        
        # Add key metrics cards (limit to important ones)
        important_metrics = []
        for metric_name, value in parsed_metrics:
            if any(keyword in metric_name.lower() for keyword in 
                   ['request', 'response', 'duration', 'total', 'count', 'size']):
                important_metrics.append((metric_name, value))
        
        # Show top 12 important metrics
        for metric_name, value in important_metrics[:12]:
            display_name = metric_name.replace('_', ' ').replace('fastapi', 'API').title()
            if isinstance(value, float):
                if value < 1:
                    display_value = f"{value:.3f}"
                elif value < 1000:
                    display_value = f"{value:.1f}"
                else:
                    display_value = f"{value:,.0f}"
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
                <h3>📋 Complete Metrics Data</h3>
                <pre>{metrics_text}</pre>
            </div>
            
            <script>
                let autoRefresh = true;
                let refreshInterval;
                
                function updateTimestamp() {{
                    document.getElementById('timestamp').textContent = new Date().toLocaleString();
                }}
                
                function toggleAutoRefresh() {{
                    autoRefresh = !autoRefresh;
                    const statusEl = document.getElementById('auto-status');
                    
                    if (autoRefresh) {{
                        statusEl.textContent = 'Auto: ON';
                        refreshInterval = setInterval(() => location.reload(), 30000);
                    }} else {{
                        statusEl.textContent = 'Auto: OFF';
                        clearInterval(refreshInterval);
                    }}
                }}
                
                // Initialize
                updateTimestamp();
                if (autoRefresh) {{
                    refreshInterval = setInterval(() => location.reload(), 30000);
                }}
            </script>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Metrics Error</title></head>
        <body style="font-family: sans-serif; padding: 20px; text-align: center;">
            <h1>❌ Error Loading Metrics</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <p>Make sure the backend is running and <code>/metrics</code> endpoint is accessible.</p>
            <button onclick="location.reload()" style="padding: 10px 20px; font-size: 16px;">🔄 Try Again</button>
        </body>
        </html>
        """
'''
    
    print("📊 Simple Metrics Viewer Code")
    print("=" * 50)
    print("Add this code to your main.py file:")
    print(viewer_code)
    
    # Also write to a file for easy copying
    with open("metrics_viewer_code.txt", "w") as f:
        f.write(viewer_code)
    
    print("\n✅ Code also saved to: metrics_viewer_code.txt")
    print("\n🌐 After adding to main.py, visit:")
    print("   http://localhost:8000/admin/metrics-dashboard")
    print("\n📋 Raw metrics available at:")
    print("   http://localhost:8000/metrics")

if __name__ == "__main__":
    create_simple_metrics_viewer() 