from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from typing import Dict

TEMPLATES_DIR = Path(__file__).parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_pdf(template_name: str, context: Dict) -> bytes:
    """Render template to PDF and return bytes"""
    template = env.get_template(template_name)
    html_content = template.render(**context)
    pdf = HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
    return pdf 