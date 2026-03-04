#!/usr/bin/env python3
"""Generate CrabMeasure_Users_Guide.pdf

Run from the carapace-measurement directory:
    python docs/generate_users_guide.py
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
NAVY     = HexColor('#0C2040')
BLUE     = HexColor('#2E7BC4')
TIP_BG   = HexColor('#FFF9E6')
TIP_TXT  = HexColor('#7B5800')
INFO_BG  = HexColor('#E8F5E3')
INFO_TXT = HexColor('#2D6A2D')
FOOT_BG  = HexColor('#EDEDEE')
DARK     = HexColor('#1A1A1A')

MEAS_GRN = HexColor('#4CAF50')
MEAS_ORG = HexColor('#FF9800')
MEAS_BLU = HexColor('#2196F3')
MEAS_PUR = HexColor('#9C27B0')
MEAS_CYN = HexColor('#00BCD4')

PW, PH   = A4
ML = MR  = 20 * mm
HDR_H    = 12 * mm
FTR_H    = 10 * mm
MT       = HDR_H + 6 * mm
MB       = FTR_H + 6 * mm
CW       = PW - ML - MR


# ---------------------------------------------------------------------------
# Page callbacks
# ---------------------------------------------------------------------------
def _cover_cb(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)

    canvas.setFillColor(white)
    canvas.setFont('Helvetica', 44)
    canvas.drawCentredString(PW / 2, PH * 0.58, 'CrabMeasure')

    canvas.setFont('Helvetica', 22)
    canvas.setFillColor(BLUE)
    canvas.drawCentredString(PW / 2, PH * 0.51, "User's Guide")

    canvas.setFont('Helvetica', 11)
    canvas.setFillColor(HexColor('#9BB8D8'))
    canvas.drawCentredString(PW / 2, PH * 0.445,
                             'Measuring crab carapace traits from microscope images')

    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(HexColor('#6080A0'))
    canvas.drawCentredString(PW / 2, PH * 0.18, 'For use with Windows and macOS')
    canvas.drawCentredString(PW / 2, PH * 0.155, 'Requires Python 3.10 or newer')
    canvas.restoreState()


def _page_cb(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFillColor(NAVY)
    canvas.rect(0, PH - HDR_H, PW, HDR_H, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(PW / 2, PH - HDR_H + 4 * mm, "CrabMeasure - User's Guide")
    # Footer
    canvas.setFillColor(FOOT_BG)
    canvas.rect(0, 0, PW, FTR_H, fill=1, stroke=0)
    canvas.setFillColor(HexColor('#777777'))
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(PW / 2, 3.5 * mm, f'Page {doc.page - 1}')
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def _S(name, **kw):
    return ParagraphStyle(name=name, **kw)

BODY  = _S('body',  fontName='Helvetica', fontSize=10, leading=14,
           spaceAfter=4, alignment=TA_JUSTIFY)
BODYS = _S('bodys', fontName='Helvetica', fontSize=9,  leading=13,
           spaceAfter=3, alignment=TA_JUSTIFY)
STEP_T = _S('step_t', fontName='Helvetica-Bold', fontSize=10,
            textColor=BLUE, leading=13, spaceAfter=1)
STEP_B = _S('step_b', fontName='Helvetica', fontSize=9,
            leading=13, spaceAfter=2)
CODE  = _S('code',  fontName='Courier', fontSize=9, leading=12,
           leftIndent=6 * mm, spaceAfter=2)
SUBH  = _S('subh',  fontName='Helvetica-Bold', fontSize=10,
           textColor=BLUE, spaceBefore=5, spaceAfter=3, leading=14)
TOC_L = _S('toc_l', fontName='Helvetica', fontSize=10, leading=17, textColor=BLUE)
TOC_R = _S('toc_r', fontName='Helvetica', fontSize=10, leading=17, alignment=TA_RIGHT)
TIP_S = _S('tips',  fontName='Helvetica', fontSize=9,  leading=13,
           textColor=TIP_TXT, alignment=TA_JUSTIFY)
INFO_S= _S('infos', fontName='Helvetica', fontSize=9,  leading=13,
           textColor=INFO_TXT, alignment=TA_JUSTIFY)
BULT  = _S('bult',  fontName='Helvetica', fontSize=10, leading=14,
           leftIndent=6 * mm, spaceAfter=2)


# ---------------------------------------------------------------------------
# Custom Flowables
# ---------------------------------------------------------------------------
class SecHeader(Flowable):
    """Full-width dark navy bar: 'N   Title'."""
    H = 10 * mm

    def __init__(self, num, title):
        super().__init__()
        self.num   = num
        self.title = title
        self.width = CW
        self.height = self.H

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 11)
        c.drawString(4 * mm, 3.2 * mm, f'{self.num}   {self.title}')


class _CircleBadge(Flowable):
    """Dark navy circle with white number."""
    SZ = 8 * mm

    def __init__(self, num):
        super().__init__()
        self.num    = num
        self.width  = self.SZ
        self.height = self.SZ

    def draw(self):
        c = self.canv
        r = self.SZ / 2
        c.setFillColor(NAVY)
        c.circle(r, r, r, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(r, r - 1.3 * mm, str(self.num))


class ColorSq(Flowable):
    """Small filled colour square."""
    SZ = 5 * mm

    def __init__(self, color):
        super().__init__()
        self.color  = color
        self.width  = self.SZ
        self.height = self.SZ

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.SZ, self.SZ, fill=1, stroke=0)


class _CalloutBox(Flowable):
    """Rounded coloured background box containing a list of Paragraphs."""
    PAD = 3 * mm

    def __init__(self, paras, bg, width=CW):
        super().__init__()
        self.paras  = paras
        self.bg     = bg
        self._w     = width
        self.height = 0

    def wrap(self, availW, availH):
        inner = self._w - 2 * self.PAD
        h = self.PAD
        for p in self.paras:
            _, ph = p.wrap(inner, availH)
            h += ph + 2
        h += self.PAD
        self.height = h
        return self._w, h

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self._w, self.height, 2 * mm, fill=1, stroke=0)
        y = self.height - self.PAD
        for p in self.paras:
            _, ph = p.wrap(self._w - 2 * self.PAD, self.height)
            y -= ph
            p.drawOn(c, self.PAD, y)
            y -= 2


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------
def tip_box(*texts):
    return _CalloutBox([Paragraph(t, TIP_S) for t in texts], TIP_BG)

def info_box(*texts):
    return _CalloutBox([Paragraph(t, INFO_S) for t in texts], INFO_BG)

def step(num, title, *body):
    """body items: str (body para) or 'CODE:...' (code para)."""
    badge   = _CircleBadge(num)
    content = [Paragraph(title, STEP_T)]
    for item in body:
        if isinstance(item, str) and item.startswith('CODE:'):
            content.append(Paragraph(item[5:], CODE))
        elif isinstance(item, str):
            content.append(Paragraph(item, STEP_B))
        else:
            content.append(item)
    tbl = Table(
        [[badge, content]],
        colWidths=[10 * mm, CW - 10 * mm],
        style=TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
    )
    return KeepTogether([tbl])


def meas_row(color, name, desc):
    """Coloured square + bold name + description, as a table row."""
    sq = ColorSq(color)
    nm = Paragraph(f'<b>{name}</b>',
                   _S('nm', fontName='Helvetica-Bold', fontSize=9.5, leading=13))
    ds = Paragraph(desc,
                   _S('ds', fontName='Helvetica', fontSize=9.5, leading=13, spaceAfter=2))
    return Table(
        [[sq, nm, ds]],
        colWidths=[8 * mm, 34 * mm, CW - 42 * mm],
        style=TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
    )


def toc_row(num, title, page):
    return Table(
        [[Paragraph(f'{num}.    {title}', TOC_L),
          Paragraph(str(page), TOC_R)]],
        colWidths=[CW - 12 * mm, 12 * mm],
        style=TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ])
    )


def sp(n=1):
    return Spacer(1, n * 4 * mm)


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------
def build():
    out_path = os.path.join(os.path.dirname(__file__), 'CrabMeasure_Users_Guide.pdf')

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
    )

    cover_frame   = Frame(0, 0, PW, PH, id='cover')
    content_frame = Frame(ML, MB, CW, PH - MT - MB, id='content')

    doc.addPageTemplates([
        PageTemplate(id='Cover',   frames=[cover_frame],   onPage=_cover_cb),
        PageTemplate(id='Content', frames=[content_frame], onPage=_page_cb),
    ])

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    # Cover is drawn entirely by _cover_cb; just advance to next page.
    story.append(NextPageTemplate('Content'))
    story.append(PageBreak())

    # ── Table of Contents (Page 1) ────────────────────────────────────────────
    story.append(sp(1))
    story.append(toc_row(1,  'What CrabMeasure does',               2))
    story.append(toc_row(2,  'System requirements',                  2))
    story.append(toc_row(3,  'Installation on Windows',              2))
    story.append(toc_row(4,  'Installation on macOS',                3))
    story.append(toc_row(5,  'Launching the app',                    4))
    story.append(toc_row(6,  'Preparing your image folder',          5))
    story.append(toc_row(7,  'Opening a folder and scale calibration', 5))
    story.append(toc_row(8,  'Measuring each image',                 6))
    story.append(toc_row(9,  'Saving and output files',              7))
    story.append(toc_row(10, 'Resuming a previous session',          7))
    story.append(toc_row(11, 'Settings',                             7))
    story.append(toc_row(12, 'Troubleshooting',                      8))
    story.append(toc_row(13, 'Phase 2: Automated measurement build-out', 8))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2 – Sections 1, 2, 3
    # =========================================================================

    # ── Section 1 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(1, 'What CrabMeasure does'))
    story.append(sp())
    story.append(Paragraph(
        'CrabMeasure is a desktop application for measuring five carapace traits from '
        'microscope images of red king crab (<i>Paralithodes camtschaticus</i>) or '
        'similar species. It replaces manual measurement in Image-Pro with a guided '
        'click-through interface designed for non-technical users.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph('Measurements produced (in millimetres):', BODY))
    for abbr, desc in [
        ('CW', 'Carapace width: widest left-to-right span of the carapace body'),
        ('CL', 'Carapace length: posterior margin to anterior reference point'),
        ('RW', 'Rostrum base width: left to right corner at the base of the rostrum'),
        ('OW', 'Orbital spine width: tip-to-tip across the orbital spines'),
        ('SL', 'First lateral spine length: from spine base to spine tip'),
    ]:
        story.append(Paragraph(
            f'  <b>{abbr}</b>  \u2013\u2013  {desc}',
            _S('ml', fontName='Helvetica', fontSize=10, leading=14,
               leftIndent=6 * mm, spaceAfter=1)))
    story.append(sp(0.5))
    story.append(Paragraph(
        'Results are written to a CSV file automatically after each image is measured.',
        BODY))
    story.append(sp())

    # ── Section 2 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(2, 'System requirements'))
    story.append(sp())
    for line in [
        '- Windows 10 or 11 (64-bit)  \u2013\u2013or\u2013\u2013  macOS 12 or newer',
        '- Python 3.10, 3.11, or 3.12  (download free from python.org)',
        '- At least 4\u202FGB of RAM and 2\u202FGB of free disk space',
        '- Internet access during installation (to download packages)',
    ]:
        story.append(Paragraph(line, BULT))
    story.append(sp(0.5))
    story.append(Paragraph(
        'No other software is required. All dependencies are installed automatically.',
        BODY))
    story.append(sp())

    # ── Section 3 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(3, 'Installation on Windows'))
    story.append(sp())
    story.append(Paragraph(
        'Complete these steps once. After that, only steps\u202F1\u20132 of '
        'Section\u202F5 are needed each time you use CrabMeasure.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph('<b>Step-by-step</b>', SUBH))

    story.append(step(1, 'Download the code',
        'Go to the project repository page. Click the green <b>Code</b> button, '
        'then click \u2018Download ZIP\u2019. Save it to your Documents folder. '
        'Right-click the ZIP file and choose \u2018Extract All\u2019. '
        'This creates a folder called carapace-measurement.'))

    story.append(step(2, 'Open Command Prompt',
        'Click the <b>search icon</b> at the lower-left corner of the screen. '
        'Type <b>cmd</b> in the search bar and press Enter. '
        'A black terminal window opens.'))

    story.append(step(3, 'Navigate to the project folder',
        'Type the command below and press Enter (adjust the path to match where you '
        'extracted the files):',
        'CODE:cd C:\\Users\\YourName\\Documents\\carapace-measurement\\carapace-measurement'))

    story.append(step(4, 'Create a virtual environment',
        'First, confirm Python is available by typing the command below and pressing Enter:',
        'CODE:py -V',
        'This should print a Python version number (e.g. <i>Python 3.11.0</i>). '
        'Then create the virtual environment:',
        'CODE:py -m venv .venv',
        'This creates a private Python environment for CrabMeasure.'))

    story.append(step(5, 'Activate the virtual environment',
        'Type the command below and press Enter:',
        'CODE:.venv\\Scripts\\activate',
        'You will see <b>(.venv)</b> at the start of the line when activation succeeds.'))

    story.append(step(6, 'Install all required packages',
        'Type the command below and press Enter. This downloads and installs all '
        'dependencies and may take 2\u201310 minutes:',
        'CODE:pip install -r requirements.txt'))

    story.append(step(7, 'Launch the app',
        'Type the command below and press Enter:',
        'CODE:python -m src.app',
        'The CrabMeasure window will open.'))

    story.append(sp(0.5))
    story.append(tip_box(
        'If you see an error \u201cpython is not recognized\u201d, try using '
        '<b>python3</b> instead of <b>python</b>. If it still fails, re-run the '
        'Python installer from python.org and tick the checkbox \u201cAdd Python '
        'to PATH\u201d at the bottom of the first screen.'))
    story.append(sp())

    # =========================================================================
    # Sections 4, 5
    # =========================================================================

    # ── Section 4 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(4, 'Installation on macOS'))
    story.append(sp())
    story.append(Paragraph(
        'Complete these steps once. After that, only steps\u202F1\u20132 of '
        'Section\u202F5 are needed each time you use CrabMeasure.',
        BODY))
    story.append(sp(0.5))

    story.append(step(1, 'Download the code',
        'Go to the project repository and download the ZIP. Save it to your Desktop '
        'or Documents folder and double-click to extract it.'))

    story.append(step(2, 'Open Terminal',
        'Press <b>Cmd + Space</b>, type <b>Terminal</b> and press Return.'))

    story.append(step(3, 'Navigate to the project folder',
        'Type the command below (adjust the path):',
        'CODE:cd ~/Desktop/carapace-measurement/carapace-measurement'))

    story.append(step(4, 'Create a virtual environment',
        'CODE:python3 -m venv .venv'))

    story.append(step(5, 'Activate the virtual environment',
        'CODE:source .venv/bin/activate',
        'You will see <b>(.venv)</b> at the start of the line when activation succeeds.'))

    story.append(step(6, 'Install all required packages',
        'CODE:pip install -r requirements.txt',
        'This may take 2\u201310 minutes.'))

    story.append(step(7, 'Launch the app',
        'CODE:python3 -m src.app'))

    story.append(sp(0.5))
    story.append(info_box(
        'Once installed you only need to: open Terminal, navigate to the folder, '
        'run <b>source .venv/bin/activate</b>, and then '
        '<b>python3 -m src.app</b> each time.'))
    story.append(sp())

    # ── Section 5 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(5, 'Launching the app'))
    story.append(sp())
    story.append(Paragraph('<b>Windows</b> (every time you use the app)', SUBH))
    for line in [
        '1.  Open Command Prompt (Windows key \u2192 type cmd \u2192 Enter)',
        '2.  cd  to your CrabMeasure folder',
        '3.  .venv\\Scripts\\activate',
        '4.  python -m src.app',
    ]:
        story.append(Paragraph(line, BULT))
    story.append(sp(0.5))
    story.append(Paragraph('<b>macOS</b> (every time you use the app)', SUBH))
    for line in [
        '1.  Open Terminal',
        '2.  cd  to your CrabMeasure folder',
        '3.  source .venv/bin/activate',
        '4.  python3 -m src.app',
    ]:
        story.append(Paragraph(line, BULT))
    story.append(sp(0.5))
    story.append(Paragraph(
        'The CrabMeasure window opens. The control panel is on the right side. '
        'The main image area on the left is blank until you open a folder.',
        BODY))
    story.append(sp(0.5))
    story.append(tip_box(
        'Do <b>NOT</b> close the Command Prompt / Terminal window while using the app. '
        'Closing the terminal also closes CrabMeasure and may lose unsaved progress.'))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4 – Sections 6, 7
    # =========================================================================

    # ── Section 6 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(6, 'Preparing your image folder'))
    story.append(sp())
    story.append(Paragraph(
        'Before using CrabMeasure, prepare <b>ONE</b> folder on your computer '
        'that contains:', BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        '1.  One calibration image whose filename includes the word  <b>micrometer</b>',
        BULT))
    story.append(Paragraph(
        '     Example:  2mm micrometer 01-30-25 1.tif',
        _S('ex', fontName='Helvetica-Oblique', fontSize=9.5, leading=13,
           leftIndent=12 * mm, spaceAfter=4)))
    story.append(Paragraph(
        '2.  Any number of carapace images (TIFF or PNG format)', BULT))
    story.append(Paragraph(
        '     Example:  T1 #21 molt 1-26-25 1.tif',
        _S('ex2', fontName='Helvetica-Oblique', fontSize=9.5, leading=13,
           leftIndent=12 * mm, spaceAfter=4)))
    story.append(sp(0.5))
    story.append(Paragraph(
        'All images must be in the same folder. Subfolders are not searched.', BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        'You will be prompted to choose this folder when you click <b>Open Folder</b> '
        'in the app. CrabMeasure saves results automatically to a sub-folder called '
        '<b>outputs</b> inside your image folder \u2013 you do <b>NOT</b> need to '
        'choose a save location separately.',
        BODY))
    story.append(sp(0.5))
    story.append(info_box(
        'Output files are always saved to:  '
        '<b>&lt;your image folder&gt;\\outputs\\measurements.csv</b>',
        'Example: if your images are in C:\\Users\\YourName\\Crabs, the results '
        'will be saved to C:\\Users\\YourName\\Crabs\\outputs\\measurements.csv',
        'This folder is created automatically \u2013 you do not need to create '
        'it yourself.'))
    story.append(sp())

    # ── Section 7 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(7, 'Opening a folder and scale calibration'))
    story.append(sp())
    story.append(Paragraph('<b>Opening a folder</b>', SUBH))
    story.append(Paragraph(
        'Click the <b>Open Folder</b> button in the control panel. A file browser '
        'window will appear. Navigate to the folder containing your images and click '
        '<b>Select Folder</b> (Windows) or <b>Open</b> (macOS).',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        'If you have demo images installed, click <b>Demo Mode</b> to practise the '
        'workflow using example images that come with the software.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph('<b>Automatic scale calibration</b>', SUBH))
    story.append(Paragraph(
        'CrabMeasure reads the micrometer image automatically and computes the scale '
        '(pixels per millimetre). The status bar shows something like:', BODY))
    story.append(Paragraph(
        'Scale: 322.50\u202Fpx/mm  (2mm micrometer 01-30-25 1.tif)',
        _S('status', fontName='Courier', fontSize=9.5, leading=14,
           leftIndent=8 * mm, spaceAfter=4)))
    story.append(Paragraph(
        'The default assumed scale bar length is 2.0\u202Fmm. If your bar is a '
        'different length, click <b>Settings\u2026</b> first and update the '
        '<b>Scale bar length</b> value.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph('<b>If automatic calibration fails</b>', SUBH))
    story.append(Paragraph(
        'If the scale bar cannot be found automatically, the app shows the micrometer '
        'image and asks you to click manually:',
        BODY))
    for line in [
        '1.  Click one end of the scale bar in the image',
        '2.  Click the other end',
        '3.  Click <b>Confirm Calibration</b> in the control panel',
    ]:
        story.append(Paragraph(line, BULT))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5 – Section 8
    # =========================================================================
    story.append(SecHeader(8, 'Measuring each image'))
    story.append(sp())
    story.append(Paragraph('<b>Auto-detected points (gold dots)</b>', SUBH))
    story.append(Paragraph(
        'When an image loads, CrabMeasure uses image analysis to estimate the '
        'carapace width (CW) and carapace length (CL) landmarks automatically. '
        'These appear as gold dots on the image. The checklist marks them '
        '<b>[A]</b> in amber.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        'You do <b>NOT</b> need to click these \u2013 they have been placed for you. '
        'If an auto-detected point looks wrong, click <b>Clear Clicks</b> to remove '
        'all points and place them all manually.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        '<b>Manual clicks \u2013 placed in the order shown in the checklist</b>', SUBH))
    story.append(Paragraph(
        'The Click Protocol checklist on the right guides you through each remaining '
        'step. An arrow (<b>\u2192</b>) marks the next click to place.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        'To place a click: left-click anywhere on the image. The dot appears and '
        'the checklist advances to the next step automatically.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        '<b>TIP:</b> Use the scroll wheel to zoom in before placing each click. '
        'Middle-mouse-drag (or two-finger trackpad drag) pans the image.',
        BODY))
    story.append(sp(0.5))

    story.append(meas_row(MEAS_GRN, 'CW_L / CW_R',
        'Carapace width \u2013 click the leftmost then rightmost widest margins of '
        'the carapace body (not spine tips). A green line appears.'))
    story.append(meas_row(MEAS_ORG, 'CL_P / CL_A',
        'Carapace length \u2013 click the rear (posterior) margin, then the front '
        '(anterior) reference point on the main carapace body. An orange line appears.'))
    story.append(meas_row(MEAS_BLU, 'RW_L / RW_R',
        'Rostrum base width \u2013 click the left then right corner at the BASE of '
        'the rostrum (the beak at the front). Do not click the rostrum tip. '
        'Blue line appears.'))
    story.append(meas_row(MEAS_PUR, 'OW_L / OW_R',
        'Orbital spine width \u2013 click the TIP of the left orbital spine, then '
        'the tip of the right orbital spine. A violet line appears.'))
    story.append(meas_row(MEAS_CYN, 'SL_B / SL_T',
        'First lateral spine length \u2013 click the BASE (root) where the first '
        'spine meets the carapace margin, then the TIP of that spine. '
        'A cyan line appears.'))

    story.append(sp(0.5))
    story.append(Paragraph('<b>After the final click</b>', SUBH))
    story.append(Paragraph(
        'Once all 10 clicks are placed (12 if measuring both lateral spines), '
        'CrabMeasure saves the measurements automatically. The status bar shows '
        'all five values in millimetres. Click <b>Next</b> to move to the '
        'next image.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph('<b>Navigation buttons</b>', SUBH))
    for label, desc in [
        ('Next',        'advance to the next unmeasured image'),
        ('Back',        'return to the previous image'),
        ('Clear Clicks','remove all clicks and start again on the current image'),
    ]:
        story.append(Paragraph(
            f'  <b>{label:<14}</b>\u2013\u2013  {desc}',
            _S('nav', fontName='Helvetica', fontSize=10, leading=14,
               leftIndent=4 * mm, spaceAfter=2)))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6 – Sections 9, 10, 11
    # =========================================================================

    # ── Section 9 ─────────────────────────────────────────────────────────────
    story.append(SecHeader(9, 'Saving and output files'))
    story.append(sp())
    story.append(Paragraph(
        'CrabMeasure saves results automatically. You do not need to press a Save '
        'button. Three files are created inside a folder called <b>outputs</b> '
        'within your image folder:',
        BODY))
    story.append(sp(0.5))

    for fname, fdesc in [
        ('measurements.csv',
         'One row per image. Columns: <i>file, px_per_mm, CW_mm, CL_mm, RW_mm, '
         'OW_mm, SL_mm</i> (and optionally <i>SL_L_mm, SL_R_mm</i> when SL\u202F'
         'mode is BOTH). Updated after every image; new rows are appended if the '
         'file already exists.'),
        ('qc_overlays/',
         'A PNG image for each measured carapace showing the image with all '
         'measurement lines drawn on top. Use these to visually verify that '
         'clicks were placed correctly.'),
        ('progress.json',
         'Tracks which images have been completed and stores the current scale. '
         'Used by the resume feature (Section\u202F10). Do not edit this file manually.'),
    ]:
        story.append(Paragraph(
            f'<b>{fname}</b>',
            _S('fn', fontName='Helvetica-Bold', fontSize=10, leading=13,
               leftIndent=4 * mm, spaceAfter=1)))
        story.append(Paragraph(
            fdesc,
            _S('fd', fontName='Helvetica', fontSize=9.5, leading=13,
               leftIndent=10 * mm, spaceAfter=5)))

    story.append(sp())

    # ── Section 10 ────────────────────────────────────────────────────────────
    story.append(SecHeader(10, 'Resuming a previous session'))
    story.append(sp())
    story.append(Paragraph(
        'If you close CrabMeasure before finishing a folder you can resume where '
        'you left off:',
        BODY))
    story.append(sp(0.5))
    for line in [
        '1.  Open CrabMeasure.',
        '2.  Click <b>Open Folder</b> and choose the same folder you were working in.',
        '3.  A dialog will ask: <i>"Resume from where you left off?"</i> \u2013 '
            'click <b>Yes</b>.',
        '4.  CrabMeasure skips already-measured images and goes straight to the '
            'next one.',
    ]:
        story.append(Paragraph(line, BULT))
    story.append(sp(0.5))
    story.append(Paragraph(
        'Measurements already recorded are preserved in <b>measurements.csv</b>. '
        'To re-measure an image that was already completed, use <b>Back</b> to '
        'navigate to it and click <b>Clear Clicks</b>.',
        BODY))
    story.append(sp())

    # ── Section 11 ────────────────────────────────────────────────────────────
    story.append(SecHeader(11, 'Settings'))
    story.append(sp())
    story.append(Paragraph(
        'Click <b>Settings\u2026</b> in the control panel to open the settings '
        'dialog. Changes take effect immediately.',
        BODY))
    story.append(sp(0.5))

    for setting, default, desc in [
        ('Scale bar length (mm)', '2.0',
         'The known length of the micrometer scale bar. Change this if your '
         'calibration image uses a scale bar of a different length.'),
        ('Micrometer keyword', 'micrometer',
         'Text that must appear somewhere in the calibration image filename '
         '(case-insensitive). Change this if your calibration image uses a '
         'different naming convention.'),
        ('Lateral spine side', 'LEFT',
         'Controls which lateral spine is measured. '
         '<b>LEFT</b> or <b>RIGHT</b> requires 10 clicks. '
         '<b>BOTH</b> measures both spines and averages them, requiring '
         '12 clicks per image.'),
    ]:
        story.append(Paragraph(
            f'<b>{setting}</b>  \u2013  default: <i>{default}</i>',
            _S('sl', fontName='Helvetica-Bold', fontSize=10, leading=13,
               leftIndent=4 * mm, spaceAfter=1)))
        story.append(Paragraph(
            desc,
            _S('sd', fontName='Helvetica', fontSize=9.5, leading=13,
               leftIndent=10 * mm, spaceAfter=5)))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7 – Sections 12, 13
    # =========================================================================

    # ── Section 12 ────────────────────────────────────────────────────────────
    story.append(SecHeader(12, 'Troubleshooting'))
    story.append(sp())

    for problem, solution in [
        ('The app does not open',
         'Confirm that you have activated the virtual environment '
         '(<b>.venv\\Scripts\\activate</b> on Windows or '
         '<b>source .venv/bin/activate</b> on macOS) before running '
         '<b>python -m src.app</b>.'),
        ('"python is not recognized" error (Windows)',
         'Re-run the Python installer from python.org. On the first screen, tick '
         'the checkbox labelled \u201cAdd Python to PATH\u201d before clicking '
         'Install Now.'),
        ('Scale calibration fails',
         'Confirm that your calibration image filename contains the word '
         '<b>micrometer</b> (or whatever keyword is set in Settings\u2026). '
         'The check is case-insensitive.'),
        ('No images appear after opening a folder',
         'CrabMeasure looks for <b>.tif</b>, <b>.tiff</b>, and <b>.png</b> files '
         'in the selected folder. Check that your images are in one of those formats '
         'and that you selected the correct folder. Subfolders are not searched.'),
        ('Measurements look wrong',
         'Open the <b>qc_overlays/</b> folder inside your output folder and review '
         'the annotated images. If lines are misplaced, navigate to that image with '
         '<b>Back</b>, click <b>Clear Clicks</b>, and re-place the points.'),
        ('The app crashes or freezes',
         'Close the terminal, re-open it, activate the virtual environment, and '
         'restart. Your progress is saved in <b>progress.json</b> so no work '
         'should be lost.'),
    ]:
        story.append(Paragraph(
            f'<b>{problem}</b>',
            _S('pb', fontName='Helvetica-Bold', fontSize=10, leading=13,
               leftIndent=0, spaceAfter=1)))
        story.append(Paragraph(
            solution,
            _S('so', fontName='Helvetica', fontSize=9.5, leading=13,
               leftIndent=8 * mm, spaceAfter=6)))

    story.append(sp())

    # ── Section 13 ────────────────────────────────────────────────────────────
    story.append(SecHeader(13, 'Phase 2: Automated measurement build-out'))
    story.append(sp())
    story.append(Paragraph('<b>Overview</b>', SUBH))
    story.append(Paragraph(
        'Phase 2 will add a semi-automated measurement pipeline to CrabMeasure. '
        'Computer vision algorithms will detect all five landmark pairs automatically, '
        'reducing manual effort per image and enabling higher-throughput processing '
        'of large image batches.',
        BODY))
    story.append(sp(0.5))

    story.append(Paragraph('<b>Role of the 20 test images</b>', SUBH))
    story.append(Paragraph(
        'A set of 20 carapace images has been designated as the Phase 2 test set. '
        'These images were selected to represent the full range of crab sizes, '
        'imaging conditions, and moult stages present in the study. Each image has '
        'been manually measured using Phase 1 of CrabMeasure, producing a set '
        'of reference (ground-truth) measurements stored in '
        '<b>data/test_set/</b>.',
        BODY))
    story.append(sp(0.5))
    story.append(Paragraph(
        'The 20 test images will be used in three ways during Phase 2 development:',
        BODY))
    story.append(sp(0.3))

    story.append(step(1, 'Algorithm development and tuning',
        'Candidate landmark-detection algorithms are run on all 20 images and their '
        'outputs are compared against the manual reference clicks. Euclidean distance '
        'in pixels and the resulting measurement error in millimetres are computed '
        'for each landmark pair. Results guide iterative refinement of the algorithm.'))

    story.append(step(2, 'Accuracy validation',
        'Once a candidate algorithm meets the target accuracy threshold '
        '(mean absolute error \u2264 0.10\u202Fmm on all five measurements), '
        'the full test set is used for formal validation. Summary statistics '
        'reported include: mean absolute error (MAE), root-mean-square error (RMSE), '
        'and the percentage of images within \u00b15\u202F% of the manual measurement.'))

    story.append(step(3, 'Regression testing',
        'Any future change to the detection pipeline is validated against the same '
        '20 images before release, ensuring that accuracy is not degraded between '
        'software versions. The test set and its manual measurements are committed '
        'to the repository and must not be altered without approval.'))

    story.append(sp(0.5))
    story.append(Paragraph('<b>Workflow integration</b>', SUBH))
    story.append(Paragraph(
        'In Phase 2, CrabMeasure will offer an <b>Auto-measure</b> button. '
        'Clicking it runs the automated detector and pre-fills all click positions. '
        'The user reviews the suggested positions, corrects any that look wrong, '
        'and then confirms. This keeps the user in the loop while greatly reducing '
        'the number of manual interactions required per image.',
        BODY))
    story.append(sp(0.5))
    story.append(info_box(
        'The 20 test images and their manual reference measurements are stored in '
        '<b>data/test_set/</b> and committed to the project repository. They are '
        'not loaded or used during normal measurement sessions.'))

    # ── Render ────────────────────────────────────────────────────────────────
    doc.build(story)
    print(f'PDF written to {out_path}')


if __name__ == '__main__':
    build()
