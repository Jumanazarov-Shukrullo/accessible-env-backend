from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Optional

# Try to import WeasyPrint, but don't fail if dependencies are missing
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError as e:
    print(f"WeasyPrint not available: {e}")
    WEASYPRINT_AVAILABLE = False
    HTML = None

TEMPLATES_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_pdf(template_name: str, context: Dict) -> Optional[bytes]:
    """Render template to PDF and return bytes"""
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("PDF generation is not available. WeasyPrint dependencies are missing.")
    
    template = env.get_template(template_name)
    html_content = template.render(**context)
    pdf = HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
    return pdf 