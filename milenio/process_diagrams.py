"""Portable SVG process maps generated directly from the governed definitions."""
import textwrap
from html import escape


def process_svg(process):
    nodes = process['nodes']
    lanes = list(dict.fromkeys(node['lane'] for node in nodes))
    width, column, step = max(1000, len(lanes) * 280), 280, 122
    height = 120 + len(nodes) * step
    positions = {node['id']: (30 + lanes.index(node['lane']) * column, 95 + i * step)
                 for i, node in enumerate(nodes)}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           '<title>' + escape(process['title']) + '</title>',
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#617683"/></marker></defs>',
           '<rect width="100%" height="100%" fill="#faf8f2"/>']
    for i, lane in enumerate(lanes):
        x = 15 + i * column
        svg.extend([f'<rect x="{x}" y="45" width="270" height="{height-60}" fill="{"#edf1f2" if i%2==0 else "#f5efe4"}"/>',
                    f'<text x="{x+15}" y="75" font-family="Segoe UI,Arial" font-size="15" fill="#182b3a">{escape(lane)}</text>'])
    for edge in process['transitions']:
        x1, y1 = positions[edge['from']]; x2, y2 = positions[edge['to']]
        startx, starty, endx, endy = x1+115, y1+80, x2+115, y2
        bend = starty+20
        svg.append(f'<path d="M{startx},{starty} V{bend} H{endx} V{endy}" fill="none" stroke="#617683" stroke-width="1.5" marker-end="url(#arrow)"><title>{escape(edge["condition"])}</title></path>')
        if x1 != x2:
            label = escape(textwrap.shorten(edge['condition'], width=37, placeholder='…'))
            svg.append(f'<text x="{min(startx,endx)+6}" y="{bend-4}" font-family="Segoe UI,Arial" font-size="10" fill="#465b67">{label}</text>')
    for node in nodes:
        x, y = positions[node['id']]
        fill = '#f4dfc4' if node['type']=='decision' else '#dce9e8' if node['type'] in ('start','end') else '#fffdf8'
        svg.append(f'<rect x="{x}" y="{y}" width="240" height="80" rx="{20 if node["type"] in ("start","end") else 5}" fill="{fill}" stroke="#8c9d9c"/>')
        for line, label in enumerate(textwrap.wrap(node['label'], width=31)[:3]):
            svg.append(f'<text x="{x+10}" y="{y+20+line*16}" font-family="Segoe UI,Arial" font-size="12" fill="#182b3a">{escape(label)}</text>')
        svg.append(f'<text x="{x+10}" y="{y+72}" font-family="Segoe UI,Arial" font-size="9" fill="#756447">{escape(node["owner"])} · {escape(node["id"])}</text>')
    return ''.join(svg) + '</svg>'
