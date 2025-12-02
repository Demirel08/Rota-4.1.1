from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from datetime import datetime, timedelta

class PDFEngine:
    """
    EFES ROTA - Raporlama Motoru
    DÜZELTİLMİŞ VERSİYON (Veri Yapısı Uyumlu) ✅
    """
    
    def __init__(self, filename="Rapor.pdf"):
        self.filename = filename
        self.register_fonts()
        
    def register_fonts(self):
        """Türkçe karakterler için font ayarı"""
        try:
            # Windows Arial fontunu dene
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Arial', font_path))
                pdfmetrics.registerFont(TTFont('Arial-Bold', "C:\\Windows\\Fonts\\arialbd.ttf"))
                self.font_normal = "Arial"
                self.font_bold = "Arial-Bold"
            else:
                self.font_normal = "Helvetica"
                self.font_bold = "Helvetica-Bold"
        except:
            self.font_normal = "Helvetica"
            self.font_bold = "Helvetica-Bold"

    def generate_production_report(self, data, start_date, end_date):
        """(Standart Rapor - Değişmedi)"""
        doc = SimpleDocTemplate(self.filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        style_title = ParagraphStyle('TitleTR', parent=styles['Title'], fontName=self.font_bold, fontSize=16)
        style_normal = ParagraphStyle('NormalTR', parent=styles['Normal'], fontName=self.font_normal, fontSize=10)

        elements.append(Paragraph("ÜRETİM HAREKET RAPORU", style_title))
        elements.append(Paragraph(f"Tarih Aralığı: {start_date} - {end_date}", style_normal))
        elements.append(Spacer(1, 20))
        
        table_data = [['TARİH', 'SİPARİŞ', 'MÜŞTERİ', 'İSTASYON', 'DURUM', 'OPERATÖR']]
        for row in data:
            try: dt = datetime.strptime(row['islem_tarihi'], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            except: dt = row['islem_tarihi']
            
            table_data.append([dt, row['siparis_no'], row['musteri'][:20], row['istasyon'], row['islem'], row['operator']])
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), self.font_normal),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        
        try:
            doc.build(elements)
            return True, self.filename
        except Exception as e:
            return False, str(e)

    # --- GÜNCELLENEN KISIM ---
    def generate_weekly_schedule_pdf(self, schedule_data):
        """
        Haftalık planı PDF'e döker.
        schedule_data formatı: { 'KESİM': [ [Gun0_Isleri], [Gun1_Isleri]... ] }
        """
        doc = SimpleDocTemplate(self.filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        style_h1 = ParagraphStyle('H1', parent=styles['Title'], fontName=self.font_bold, fontSize=18, spaceAfter=20)
        style_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName=self.font_bold, fontSize=14, spaceBefore=15, textColor=colors.darkblue)
        style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontName=self.font_normal, fontSize=9)

        elements.append(Paragraph("HAFTALIK ÜRETİM İŞ EMRİ LİSTESİ", style_h1))
        elements.append(Paragraph(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", style_cell))
        elements.append(Spacer(1, 20))

        today = datetime.now()
        tr_days = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]
        machines = ["KESİM", "RODAJ", "DELİK", "TEMPER", "LAMİNE", "ISICAM", "KUMLAMA", "SEVKİYAT"]

        # 7 Gün İçin Döngü
        for day_idx in range(7):
            day_date = today + timedelta(days=day_idx)
            day_title = f"{tr_days[day_date.weekday()]} - {day_date.strftime('%d.%m.%Y')}"
            
            elements.append(Paragraph(day_title, style_h2))
            
            table_data = [['İSTASYON', 'PLANLANAN İŞLER']]
            has_data = False
            
            for machine in machines:
                machine_key = machine.upper()
                
                # --- DÜZELTME BURADA ---
                # Veriyi Makine -> Gün İndeksi sırasıyla çekiyoruz
                orders = []
                try:
                    if machine_key in schedule_data:
                        if len(schedule_data[machine_key]) > day_idx:
                            orders = schedule_data[machine_key][day_idx]
                except:
                    orders = []
                # -----------------------
                
                if orders:
                    has_data = True
                    job_lines = []
                    for o in orders:
                        # o: {'code':..., 'customer':..., 'm2':...}
                        line = f"• {o.get('code','?')} ({o.get('customer','?')}) - {o.get('m2',0):.1f} m2"
                        job_lines.append(line)
                    
                    content = "\n".join(job_lines)
                else:
                    content = "-"
                
                table_data.append([machine, Paragraph(content.replace("\n", "<br/>"), style_cell)])

            if has_data:
                t = Table(table_data, colWidths=[100, 400])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, -1), self.font_bold),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 15))
            else:
                elements.append(Paragraph("<i>Bu gün için planlanmış iş bulunmamaktadır.</i>", style_cell))
                elements.append(Spacer(1, 15))
            
            if day_idx == 2: 
                elements.append(PageBreak())

        try:
            doc.build(elements)
            return True, self.filename
        except Exception as e:
            return False, str(e)