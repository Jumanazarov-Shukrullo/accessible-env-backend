#!/usr/bin/env python3
"""
Setup Prometheus monitoring with Grafana for your FastAPI app
"""

def setup_grafana_docker():
    """Instructions for setting up Grafana with Docker"""
    print("🐳 Quick Grafana Setup with Docker")
    print("=" * 50)
    
    print("\n1. Start Grafana container:")
    print("   docker run -d -p 3000:3000 --name grafana grafana/grafana-oss")
    
    print("\n2. Access Grafana:")
    print("   URL: http://localhost:3000")
    print("   Login: admin / admin")
    
    print("\n3. Add Prometheus data source:")
    print("   - Go to Configuration > Data Sources")
    print("   - Add Prometheus")
    print("   - URL: http://host.docker.internal:8000/metrics")
    print("   - (or http://localhost:8000/metrics if running locally)")
    
    print("\n4. Import FastAPI dashboard:")
    print("   - Go to + > Import")
    print("   - Use dashboard ID: 14200 (FastAPI Observability)")
    print("   - Or create custom dashboards")

def setup_prometheus_server():
    """Instructions for setting up full Prometheus server"""
    print("\n📊 Full Prometheus + Grafana Setup")
    print("=" * 50)
    
    prometheus_config = """
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
"""
    
    docker_compose = """
# docker-compose.yml for Prometheus + Grafana
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana-oss:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
"""
    
    print("Create these files:")
    print("\n📄 prometheus.yml:")
    print(prometheus_config)
    
    print("\n📄 docker-compose.yml:")
    print(docker_compose)
    
    print("\nThen run:")
    print("   docker-compose up -d")
    
    print("\nAccess:")
    print("   Prometheus: http://localhost:9090")
    print("   Grafana: http://localhost:3000 (admin/admin)")

def simple_browser_view():
    """Simple browser-based viewing options"""
    print("\n🌐 Simple Browser Options")
    print("=" * 50)
    
    print("1. Raw metrics (what you already have):")
    print("   http://localhost:8000/metrics")
    
    print("\n2. Prometheus Expression Browser:")
    print("   - Install Prometheus locally")
    print("   - Configure it to scrape your app")
    print("   - Use http://localhost:9090 for queries")
    
    print("\n3. Browser extensions:")
    print("   - 'Prometheus Metrics Viewer' Chrome extension")
    print("   - 'JSON Formatter' for better readability")

def create_monitoring_files():
    """Create the actual config files"""
    
    # Create prometheus.yml
    prometheus_config = """global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['host.docker.internal:8000']  # For Docker on Windows/Mac
    metrics_path: '/metrics'
    scrape_interval: 5s
"""
    
    # Create docker-compose.yml
    docker_compose = """version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    extra_hosts:
      - "host.docker.internal:host-gateway"

  grafana:
    image: grafana/grafana-oss:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
"""
    
    with open("prometheus.yml", "w") as f:
        f.write(prometheus_config)
    
    with open("docker-compose.monitoring.yml", "w") as f:
        f.write(docker_compose)
    
    print("\n✅ Created monitoring configuration files:")
    print("   - prometheus.yml")
    print("   - docker-compose.monitoring.yml")

if __name__ == "__main__":
    print("🔍 Prometheus Metrics UI Setup Options")
    print("=" * 60)
    
    setup_grafana_docker()
    setup_prometheus_server()
    simple_browser_view()
    
    print("\n" + "=" * 60)
    print("🎯 Recommendations:")
    print("1. 🚀 FASTEST: Use the Grafana Docker command above")
    print("2. 📊 BEST: Use the full Prometheus + Grafana setup")
    print("3. 🔧 SIMPLE: Just view raw metrics in browser")
    
    print("\n📁 Want me to create the config files? (y/n)")
    
    # Create the files anyway for convenience
    create_monitoring_files()
    
    print("\n🚀 Quick Start Commands:")
    print("1. Start monitoring stack:")
    print("   docker-compose -f docker-compose.monitoring.yml up -d")
    print("\n2. Access dashboards:")
    print("   Prometheus: http://localhost:9090")
    print("   Grafana: http://localhost:3000")
    print("\n3. In Grafana:")
    print("   - Add Prometheus data source: http://prometheus:9090")
    print("   - Import dashboard ID: 14200 for FastAPI metrics") 