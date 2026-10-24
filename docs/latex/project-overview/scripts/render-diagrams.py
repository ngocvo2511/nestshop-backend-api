"""Refresh the portable LaTeX project's source snapshots and PlantUML images."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

project = Path(__file__).resolve().parents[1]
repo = project.parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plantuml-jar', required=True, type=Path)
args = parser.parse_args()
jar = args.plantuml_jar.resolve(strict=True)
source = repo / 'docs/diagrams/sequence'
snapshot = project / 'plantuml/sequence'
rendered = project / 'images/sequence'
for folder in [snapshot, rendered, project / 'images/architecture', project / 'images/database']:
    folder.mkdir(parents=True, exist_ok=True)

files = sorted(source.glob('SEQ-*.puml'))
assert len(files) == 32
assert [int(p.name[4:6]) for p in files] == list(range(1, 33))
for path in files:
    shutil.copy2(path, snapshot / path.name)
command = ['java', '-Xmx1024m', '-DPLANTUML_LIMIT_SIZE=10000', '-jar', str(jar), '-charset', 'UTF-8']
subprocess.run(command + ['-checkonly', '*.puml'], cwd=snapshot, check=True)
subprocess.run(command + ['-failfast2', '-Sdpi=200', '-tpng', '-o', str(rendered), '*.puml'], cwd=snapshot, check=True)
# Refresh the repository SVGs whose source labels changed with the approved baseline.
for number in [22, 25]:
    path = next(source.glob(f'SEQ-{number:02d}-*.puml'))
    subprocess.run(command + ['-tsvg', '-o', 'rendered', path.name], cwd=source, check=True)

assets = [
    ('docs/diagrams/architecture/SystemContext.png', 'images/architecture/system-context.png'),
    ('docs/diagrams/architecture/Containers (1).png', 'images/architecture/containers.png'),
    ('docs/diagrams/architecture/BackendComponents.png', 'images/architecture/backend-components.png'),
    ('docs/database/database.png', 'images/database/database.png'),
]
for src, dst in assets:
    shutil.copy2(repo / src, project / dst)

titles = ['Register an account', 'Log in', 'Refresh token', 'Log out', 'View own profile', 'Update own profile', 'Change password', 'View product list', 'View product details', 'Create product', 'Update product', 'Upload product image', 'Adjust product stock', 'View user roles', 'Create order', 'View own order list', 'View own order details', 'Cancel order', 'View fulfillment queue', 'View order details for fulfillment', 'Update order status', 'Initiate VNPay payment', 'Handle VNPay IPN', 'Handle browser return', 'Expire payment attempt', 'Expire order and release stock', 'View payment reconciliation', 'Check API health', 'Manage categories (P1)', 'Manage cart (P1)', 'Send email notification (P1)', 'Update user role']
descriptions = ['Guest registration validates input and duplicate email; public registration creates CUSTOMER only.', 'Validate credentials and account activity; failures do not reveal which credential was incorrect.', 'Rotate atomically and distinguish consumed-token replay from ordinary revocation.', 'Revoke the token family; repeated operations cannot restore a revoked session.', "Read only the authenticated user's profile without mutation.", 'Update only allowlisted fields belonging to the authenticated user.', 'Verify the current password; change its hash and revoke all refresh families atomically.', 'Return active products with validated search, filters, sorting and offset pagination.', 'Return active product details and safely handle missing or inactive products.', 'Admin creates a product with an integer-VND price and nonnegative initial stock.', 'Admin updates allowlisted catalog fields; direct stock mutation is forbidden.', 'Validate role, type and size; persist the file and clean it up if the database write fails.', 'Admin supplies a signed delta and reason; reject negative stock and persist audit atomically.', 'Admin reads role assignments; this read operation does not create a role-change audit.', 'Validate inline shipping details; calculate server totals, save snapshots and reserve stock for 60 minutes.', 'Customer receives only their own paginated orders.', "Customer reads an owned order's snapshots, payment information and status history.", 'Cancel before payment; serialize with IPN/expiry and release stock exactly once.', 'Staff/Admin reads the status-based fulfillment queue; advanced filters remain P1.', 'Staff/Admin reads eligible fulfillment details, shipping snapshots, payment summary and history.', 'Advance the next permitted fulfillment state and persist history without editing payment state.', 'Allow one pending attempt; reuse a safely valid URL or return conflict without changing stock.', 'Verify signature and persisted data; handle success, failure, duplicate, late and conflicting callbacks.', 'Browser return cannot settle payment; presentation must reflect authoritative server state.', 'Evaluate the 20-minute target; expire only safely and retain PENDING if provider finality is unresolved.', 'Expire overdue 60-minute reservations, pending attempts and history; release stock exactly once.', 'Admin reads attempts and reconciliation outcomes without settlement-edit authority.', 'A lightweight public endpoint reports health without exposing secrets.', 'Optional P1 active-category browsing and Admin category management.', 'Optional P1 customer-owned cart management without price or stock reservation.', 'Deferred P1: persist the event with business state, send after commit and recover/retry with bounds.', 'Admin changes a role through a dedicated operation with atomic actor/target/old/new/time audit.']
inventory = source.joinpath('README.md').read_text(encoding='utf-8')
rows = {}
for line in inventory.splitlines():
    match = re.match(r'\| \[SEQ-(\d+)\]', line)
    if match:
        columns = line.split('|')
        rows[int(match[1])] = (columns[3].strip(), columns[4].strip())

def tex(value):
    return value.replace('&', r'\&').replace('_', r'\_').replace('%', r'\%').replace('#', r'\#')

lines = [r'\chapter{PlantUML Sequence Diagrams}',
         'This appendix includes all 32 flows with their original SEQ identifiers. Images are rendered from the supplied PlantUML snapshots. P1 diagrams describe optional extensions rather than mandatory MVP delivery.',
         r'\section*{Grouped Index}', r'\begin{itemize}',
         r'\item Authentication and profiles: SEQ-01--07.',
         r'\item Catalog, inventory and roles: SEQ-08--14; role changes: SEQ-32.',
         r'\item Customer and Staff orders: SEQ-15--21.',
         r'\item Payments, expiration and reconciliation: SEQ-22--27.',
         r'\item Health: SEQ-28; optional P1 extensions: SEQ-29--31.', r'\end{itemize}',
         'Controllers and services are logical components of one modular monolith. SRS transaction requirements apply even where begin/commit/rollback commands are omitted. The 200-dpi PNGs can be enlarged in the PDF; PlantUML sources are included for re-export.']
for number, path in enumerate(files, 1):
    mapping, actor = rows[number]
    mapping = re.sub(r';\s*SRS \d+(?:\.\d+)?', '', mapping)
    lines.append(r'\diagram{SEQ-%02d --- %s}{seq:%02d}{%s\par\small Actor: %s. Traceability: %s.}{images/sequence/%s.png}' %
                 (number, titles[number-1], number, descriptions[number-1], tex(actor), tex(mapping), path.stem))
project.joinpath('sections/06-sequences.tex').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

records = []
for src, dst in assets:
    records.append({'source': src, 'output': dst, 'sha256': digest(project / dst), 'copy_exact': digest(repo / src) == digest(project / dst)})
for path in files:
    output = rendered / (path.stem + '.png')
    data = output.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width, height = struct.unpack('>II', data[16:24])
    records.append({'source': path.relative_to(repo).as_posix(), 'source_sha256': digest(path),
                    'snapshot': (snapshot / path.name).relative_to(project).as_posix(),
                    'output': output.relative_to(project).as_posix(), 'width': width, 'height': height, 'sha256': digest(output)})
manifest = {'date': '2026-10-29', 'srs_version': '0.9', 'renderer': 'PlantUML 1.2026.9',
            'syntax_check': '32/32 passed', 'sequence_count': 32, 'architecture_count': 3, 'database_count': 1,
            'render_arguments': ['-charset UTF-8', '-Sdpi=200', '-tpng'],
            'integration_tests': 'Not run: documentation-only workspace; no payment finality claim.', 'assets': records}
project.joinpath('build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Validated 32 PlantUML sources; rendered 32 PNGs; copied 4 original images; wrote appendix and manifest.')
