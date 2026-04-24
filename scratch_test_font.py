from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer)
styles = getSampleStyleSheet()
elements = []

elements.append(Paragraph("Test: <font name='ZapfDingbats'>&#x27A4; &#x2706; &#x2709;</font>", styles['Normal']))

doc.build(elements)
print("SUCCESS")
