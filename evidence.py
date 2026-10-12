"""Render actual execution evidence (not simulated browser screenshots)."""
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient
from main import create_app
from seed import seed


def render(name, lines):
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 19)
    except OSError:
        font = ImageFont.load_default(size=19)
    image = Image.new('RGB', (1400, max(480, 100 + 29 * len(lines))), '#101827')
    draw = ImageDraw.Draw(image)
    draw.text((30, 24), 'REAL EXECUTION OUTPUT | SQL SECURITY DEMO', font=font, fill='#51ddb2')
    for i, line in enumerate(lines):
        draw.text((30, 80 + i * 29), line, font=font, fill='#e5eaf4')
    image.save(Path('evidence') / name)


if __name__ == '__main__':
    Path('evidence').mkdir(exist_ok=True)
    output = subprocess.run(['python', '-m', 'pytest', '-q'], capture_output=True, text=True)
    Path('test-results.txt').write_text(output.stdout + output.stderr)
    render('tests.png', ['$ python -m pytest -q'] + output.stdout.splitlines())
    if output.returncode:
        raise SystemExit(output.returncode)
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / 'demo.db'
        seed(database)
        lines = ['Actual FastAPI TestClient responses', '']
        with TestClient(create_app(database)) as client:
            for sql in ['SELECT id, name, price FROM products', 'SELECT internal_cost FROM products', 'DELETE FROM products']:
                response = client.post('/query', json={'sql': sql})
                lines += ['POST /query: ' + sql, 'HTTP ' + str(response.status_code)]
                lines += json.dumps(response.json(), indent=2).splitlines() + ['']
        render('api.png', lines)
