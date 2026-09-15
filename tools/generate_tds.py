"""Build the four public, price-free technical data sheets from approved page specs."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "tds"

SHEETS = {
    "tds-is-710-marine-bwp.pdf": {
        "title": "IS 710 Marine BWP",
        "subtitle": "Boiling-waterproof hardwood-core plywood for wet service",
        "intro": "A quote-ready summary for marine joinery, hulls, decks and wet interiors. The written quotation confirms the selected thickness, finished dimensions, tolerances, availability and delivery.",
        "rows": [
            ("Standard / bond", "IS 710 BWP; 100% phenol-formaldehyde boiling-waterproof glue line"),
            ("Core", "Full hardwood veneer core, gap-free"),
            ("Thickness", "4-25 mm"),
            ("Standard sheet", "1220 x 2440 mm; custom cut-to-size available"),
            ("Face / back", "Confirmed against the written specification"),
            ("Typical use", "Boatbuilding, hulls and decks, wet interiors and marine joinery"),
            ("Options", "Preservative-treated; calibrated or sanded where specified"),
            ("Supply", "Full truckload ex-factory Perumbavoor in India; 20 ft or 40 ft container FOB Cochin for export"),
        ],
    },
    "tds-is-303-commercial-mr-bwr.pdf": {
        "title": "IS 303 Commercial MR / BWR",
        "subtitle": "Hardwood-core commercial plywood for joinery and interiors",
        "intro": "Two quoteable constructions under IS 303. Select BWR for humid or occasionally wet interiors and MR for dry furniture, cabinetry and panelling; the quotation records the grade and final construction.",
        "rows": [
            ("BWR standard / bond", "IS 303 BWR; melamine-fortified UF or phenolic glue line"),
            ("MR standard / bond", "IS 303 MR; urea-formaldehyde glue line"),
            ("Core / faces", "Hardwood or mixed hardwood, gap-free; Gurjan or keruing face options"),
            ("Thickness", "BWR 6-25 mm; MR 4-25 mm"),
            ("Standard sheet", "1220 x 2440 mm; custom cut-to-size available"),
            ("BWR use", "Kitchens, bathrooms, humid and semi-exterior interiors"),
            ("MR use", "Dry interiors, furniture, panelling and cabinetry"),
            ("Supply", "Full truckload ex-factory Perumbavoor in India; 20 ft or 40 ft container FOB Cochin for export"),
        ],
    },
    "tds-calibrated-okoume-e1.pdf": {
        "title": "Calibrated Okoume E1",
        "subtitle": "Light, calibrated Okoume-faced panel for joinery and export",
        "intro": "A concise technical summary for the dedicated calibrated panel. Okoume is a face veneer; the quotation confirms the core, bond, finish, thickness and documentation for the order.",
        "rows": [
            ("Face", "Okoume (Aucoumea klaineana), pale and uniform"),
            ("Core", "Eucalyptus core for the calibrated E1 construction"),
            ("Emission class", "E1; test report available on request"),
            ("Calibration", "Sanded to a held thickness; final tolerance confirmed in the quote"),
            ("Reference variant", "16 mm panel at approximately 32 kg per nominal 8 x 4 ft sheet"),
            ("Finish", "Bare for the buyer's finish or HPL-laminated where specified"),
            ("Other builds", "Okoume face is also available on MR IS 303 and BWR packing constructions"),
            ("Supply", "FOB Cochin export quotation; sheet size, face combination and quantity confirmed before production"),
        ],
    },
    "tds-film-faced-shuttering.pdf": {
        "title": "Film-Faced Shuttering Plywood",
        "subtitle": "High-density formwork panel for repeat concrete pours",
        "intro": "A quote-ready summary for slab decks, columns and wall forms. Actual re-use depends on handling, cleaning, support spacing and edge care; the quotation confirms the selected film weight and construction.",
        "rows": [
            ("Standard / bond", "IS 303 BWR; phenolic (WBP) bonded"),
            ("Film", "120-220 gsm dynamic-resistant phenolic film on both faces"),
            ("Core", "Full hardwood construction"),
            ("Thickness", "12, 15, 18, 21 and 25 mm; 12 mm and 18 mm most common"),
            ("Standard sheet", "1220 x 2440 mm; 1830 x 915 mm and custom sizes available"),
            ("Edges", "Acrylic-sealed against water ingress"),
            ("Expected re-use", "20-40+ pours with correct handling and edge care"),
            ("Supply", "Full truckload ex-factory Perumbavoor in India; 20 ft or 40 ft container FOB Cochin for export"),
        ],
    },
}


def build(filename, data):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=data["title"],
                            author="Cochin Wood Industries")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TdsTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21,
                           leading=25, textColor=colors.HexColor("#0E1F18"), alignment=TA_LEFT, spaceAfter=4)
    subtitle = ParagraphStyle("TdsSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5,
                              leading=14, textColor=colors.HexColor("#007A5E"), spaceAfter=12)
    body = ParagraphStyle("TdsBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2,
                          leading=13, textColor=colors.HexColor("#3A4A52"), spaceAfter=8)
    label = ParagraphStyle("TdsLabel", parent=body, fontName="Helvetica-Bold", textColor=colors.HexColor("#0E1F18"))
    small = ParagraphStyle("TdsSmall", parent=body, fontSize=7.8, leading=10.5, textColor=colors.HexColor("#5F6E76"), spaceAfter=0)
    story = [Paragraph("COCHIN WOOD INDUSTRIES", subtitle), Paragraph(data["title"], title),
             Paragraph(data["subtitle"], subtitle), Paragraph(data["intro"], body), Spacer(1, 3 * mm)]
    table_data = [[Paragraph("Attribute", label), Paragraph("Specification", label)]]
    for key, value in data["rows"]:
        table_data.append([Paragraph(key, label), Paragraph(value, body)])
    table = Table(table_data, colWidths=[48 * mm, 124 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5EFE9")),
        ("GRID", (0, 0), (-1, -1), .45, colors.HexColor("#C8D5CA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    story.extend([Spacer(1, 7 * mm), Paragraph("Commercial note", label),
                  Paragraph("This sheet contains no public price. Quantity, sheet size, destination, availability, final tolerance and delivery terms change the offer and are confirmed by the sales team in the written quotation. Email sales@cochinwood.in or use the quote form at cochinwood.in/contact.", body),
                  Paragraph("Revision 1.0 | 14 September 2026 | Product information summary - final order specification controls.", small)])
    doc.build(story)


if __name__ == "__main__":
    for name, data in SHEETS.items():
        build(name, data)
    print(f"Generated {len(SHEETS)} TDS PDFs in {OUT}")
