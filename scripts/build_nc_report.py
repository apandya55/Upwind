#!/usr/bin/env python3
"""Rebuild the three-page annual evidence report; never infer hourly exposure."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import sys
import io
import base64

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from upwind.report import static_evidence_report


def main():
    source = ROOT / 'release/upwind_nc_air_quality.parquet'
    output = ROOT / 'reports'
    output.mkdir(exist_ok=True)
    df = pd.read_parquet(source)
    df = df[df.county_fips.isin(['37063', '37119'])].copy()
    df['county'] = df.county_fips.map({'37063': 'Durham', '37119': 'Mecklenburg'})
    if df.empty:
        raise ValueError('No target county observations')
    summary = df.groupby(['year', 'county']).agg(sites=('id','nunique'), mean=('pm25_ug_m3','mean'), minimum=('pm25_ug_m3','min'), maximum=('pm25_ug_m3','max')).reset_index()
    summary.to_csv(output / 'nc-school-corridors-2026-summary.csv', index=False)
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 13
    story, pages = [], []
    titles = ['Annual evidence, not commute exposure', 'County monitor observations', 'What a corridor study must establish']
    notes = [
        f'The exported dataset contains {len(df)} annual site-years from {df.id.nunique()} physical stations in Durham and Mecklenburg counties, {df.year.min()}–{df.year.max()}. These are measured EPA annual PM2.5 summaries. The curves are unweighted means across available stations, not population exposure or school measurements. Changes in station coverage can affect year-to-year differences.',
        'The table reports all included county-years. Values are displayed to six decimal places; the accompanying CSV preserves numeric precision. Minima and maxima are annual station averages, not hourly extremes. Colocated instruments were combined upstream. No rows were removed or imputed in this county subset.',
        'Commute versus off-peak PM2.5, AQI spikes, school exposure, and the subset within 1 km of I-40 / I-85 are NOT ESTIMABLE from this export. Annual periods contain no hour-of-day observations. No road-distance or school join was performed. Missing meteorology remains null. An annual PM2.5 value must not be presented as an hourly AQI value.'
    ]
    for i in range(3):
        fig, ax = plt.subplots(figsize=(8, 3))
        for county, group in summary.groupby('county'):
            if i == 0:
                ax.plot(group.year, group['mean'], marker='o', label=county)
            elif i == 1:
                ax.plot(group.year, group.sites, marker='o', label=county)
            else:
                values = df[df.county == county].pm25_ug_m3.sort_values()
                ax.step(values, [j/len(values) for j in range(1, len(values)+1)], where='post', label=county)
        ax.set_ylabel(['Mean annual PM2.5 (µg/m³)', 'Distinct reporting stations', 'Fraction of annual site-years'][i])
        ax.set_xlabel('Annual PM2.5 (µg/m³)' if i == 2 else 'Observation year')
        ax.spines[['top','right']].set_visible(False)
        ax.grid(alpha=.15)
        ax.legend(frameon=False)
        fig.tight_layout()
        svg = output / f'nc-corridors-chart-{i+1}.svg'
        fig.savefig(svg)
        png = io.BytesIO()
        fig.savefig(png, format='png', dpi=160)
        plt.close(fig)
        page = f'<p>UPWIND / EMPIRICAL EVIDENCE NOTE / 14 NOVEMBER 2026 / {i+1} OF 3</p><h1>{titles[i]}</h1><p>{notes[i]}</p>'
        page += '<img alt="'+html.escape(titles[i])+' chart" src="data:image/svg+xml;base64,'+base64.b64encode(svg.read_bytes()).decode()+'">'
        story += [Paragraph('UPWIND | EMPIRICAL EVIDENCE NOTE | 14 NOVEMBER 2026', styles['Normal']), Spacer(1,12), Paragraph(titles[i], styles['Title']), Paragraph(notes[i], styles['BodyText']), Image(io.BytesIO(png.getvalue()), width=480, height=180)]
        if i == 0:
            text = 'Scope: annual EPA reference observations only. This report does not find or rule out traffic-related spikes. It documents the available evidence and the requirements for testing that question. The filename denotes the intended research question, not completed school-corridor validation. 2025 summaries are provisional.'
        elif i == 1:
            rows = [['Year','County','Sites','Mean','Min','Max']] + [[str(r.year), r.county, str(r.sites), f'{r.mean:.6f}', f'{r.minimum:.6f}', f'{r.maximum:.6f}'] for r in summary.itertuples()]
            page += '<table>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
            table = Table(rows, colWidths=[40,85,35,85,85,85])
            table.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),4),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf4f4'))]))
            story.append(table)
            text = 'Concentrations: µg/m³, local conditions. Station count is physical sites, not instruments.'
        else:
            text = 'Required next study: acquire quality-controlled hourly observations and weather; join verified highway centerlines using geodesic or projected point-to-line distance; identify school locations separately; define a 1,000 m buffer before examining outcomes. Pre-register weekday 07:00–09:00 and 16:00–19:00 America/New_York commute windows, matched off-peak hours, daylight-saving handling, completeness thresholds, and day-level uncertainty. Use an appropriate EPA AQI averaging protocol rather than applying breakpoints to annual averages. Spatial interpolation requires independent held-out stations and cannot create missing temporal evidence.'
        page += '<p class="note">'+text+'</p>'
        story += [Spacer(1,10), Paragraph(text, styles['BodyText'])]
        if i == 2:
            provenance = 'Source: release/upwind_nc_air_quality.parquet. SHA-256: '+hashlib.sha256(source.read_bytes()).hexdigest()
            page += '<p>'+provenance+'</p><p>Reproduce: <code>python scripts/build_nc_report.py</code>. See DATA_DICTIONARY.md and BENCHMARKS.md in the repository. Upstream: EPA AQS annual monitor summaries; scripts/build_national_dataset.py. No causal attribution, health advice, or commute-window result is asserted.</p>'
            story += [Spacer(1,10), Paragraph(provenance, styles['BodyText'])]
        pages.append(page)
        if i < 2:
            story.append(PageBreak())
    stem = 'nc-school-corridors-2026'
    (output / f'{stem}.html').write_text(static_evidence_report('UPWIND — NC annual evidence and corridor study gaps', pages))
    SimpleDocTemplate(str(output / f'{stem}.pdf'), rightMargin=42, leftMargin=42, topMargin=35, bottomMargin=35).build(story)
    assert len(PdfReader(output / f'{stem}.pdf').pages) == 3
    public = ROOT / 'frontend/public/reports'
    public.mkdir(parents=True, exist_ok=True)
    for suffix in ['html','pdf']:
        shutil.copyfile(output / f'{stem}.{suffix}', public / f'{stem}.{suffix}')
    shutil.copyfile(output / f'{stem}-summary.csv', public / f'{stem}-summary.csv')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('nc-*') if p.is_file()}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')

if __name__ == '__main__':
    main()
