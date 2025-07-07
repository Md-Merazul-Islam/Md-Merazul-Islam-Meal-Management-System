import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

def generate_pdf(order_data, message=""):
    buffer = io.BytesIO()
        
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
        
    today = datetime.today().strftime("%A, %Y-%m-%d")  
    elements.append(f"Order List for {today}\n\n")
        
    product_data = []
            
    for order in order_data:
        for item in order.items.all():
            product_name = item.product_details.name
            quantity = item.quantity
            product_data.append([product_name, quantity])
        
    if not product_data:
        product_data.append([message, ""])
        
    header = ['Product Name', 'Quantity']
        
    table = Table([header] + product_data, colWidths=[200, 60])
        
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),  
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  
        ('GRID', (0, 0), (-1, -1), 0.5, (0, 0, 0)),  
        ('FONTSIZE', (0, 0), (-1, -1), 8),  
        ('TOPPADDING', (0, 0), (-1, -1), 6),  
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  
    ])
    
    table.setStyle(style)
        
    elements.append(table)
        
    doc.build(elements)

    buffer.seek(0)
    return buffer
