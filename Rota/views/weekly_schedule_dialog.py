import sys
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QWidget, QFileDialog, QMessageBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

try:
    from ui.theme import Theme
    from core.smart_planner import planner
    from core.pdf_engine import PDFEngine
except ImportError:
    pass

class WeeklyScheduleView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Haftalık Üretim Programı")
        self.resize(1000, 700)
        self.setStyleSheet(f"background-color: {Theme.BACKGROUND};")

        # 1. VERİYİ ÇEK VE KONTROL ET
        print("\n--- HAFTALIK LİSTE OLUŞTURULUYOR ---")
        self.schedule_data = self.get_plan_data()

        self.setup_ui()

    def get_plan_data(self):
        """
        SmartPlanner'dan detaylı listeyi ister.
        """
        try:
            if 'planner' not in globals() or planner is None:
                print("❌ HATA: Planner modülü bulunamadı!")
                return {}

            # Motordan veriyi iste (Grid, Details, [FinishDate])
            result = planner.calculate_forecast()
            
            # Gelen veriyi analiz et
            details = {}
            if isinstance(result, tuple):
                # Eğer 3 veri dönüyorsa (v10 motoru) veya 2 veri dönüyorsa
                # Genelde 2. eleman details'dir.
                if len(result) >= 2:
                    details = result[1]
                    print(f"✅ Veri başarıyla alındı. {len(details.keys())} makine için veri var.")
                else:
                    print("⚠️ Veri formatı beklenenden kısa!")
            else:
                print("⚠️ Veri tuple değil!")

            return details
                
        except Exception as e:
            print(f"❌ Planlama verisi alınırken hata: {e}")
            return {}

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Başlık alanı
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("Haftalık İş Programı")
        title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 600;
            color: {Theme.TEXT_PRIMARY};
        """)
        header_layout.addWidget(title)

        sub = QLabel("Gün seçerek detaylı iş listesini görüntüleyin")
        sub.setStyleSheet(f"""
            color: {Theme.TEXT_SECONDARY};
            font-size: 14px;
        """)
        header_layout.addWidget(sub)
        layout.addLayout(header_layout)

        # Sekmeler
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Theme.BORDER_LIGHT};
                background: {Theme.SURFACE};
                border-radius: {Theme.RADIUS_MD};
                top: -1px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                padding: 12px 24px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 8px;
                font-weight: 500;
                font-size: 14px;
            }}
            QTabBar::tab:hover {{
                color: {Theme.PRIMARY};
                background-color: {Theme.SURFACE_DARK};
            }}
            QTabBar::tab:selected {{
                background: transparent;
                color: {Theme.PRIMARY};
                border-bottom: 2px solid {Theme.PRIMARY};
            }}
        """)
        
        today = datetime.now()
        tr_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        
        # 7 Günlük Sekme
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_name = tr_days[day_date.weekday()]
            tab_title = f"{day_name} ({day_date.strftime('%d.%m')})"
            
            page = self.create_day_page(i)
            self.tabs.addTab(page, tab_title)
            
        layout.addWidget(self.tabs)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_close = QPushButton("KAPAT")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedHeight(44)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.SURFACE};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: {Theme.RADIUS_SM};
                padding: 0 24px;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Theme.SURFACE_DARK};
                border-color: {Theme.PRIMARY};
            }}
        """)

        btn_print = QPushButton("PDF OLARAK INDIR")
        btn_print.setCursor(Qt.PointingHandCursor)
        btn_print.clicked.connect(self.export_to_pdf)
        btn_print.setFixedHeight(44)
        btn_print.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: white;
                border: none;
                border-radius: {Theme.RADIUS_SM};
                padding: 0 24px;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_DARK};
            }}
        """)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        btn_layout.addWidget(btn_print)

        layout.addLayout(btn_layout)

    def create_day_page(self, day_idx):
        """O günün tablosunu oluşturur"""
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        page_layout = QVBoxLayout(content_widget)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(15)
        
        # Makine İsimlerini Doğrudan Çekelim (Hata olmasın)
        machines = list(self.schedule_data.keys()) if self.schedule_data else ["KESİM", "RODAJ", "TEMPER"]
        # Sıralayalım (Opsiyonel)
        machines.sort() 
        
        has_any_job = False
        
        # DEBUG: Hangi gün için ne yapıyoruz?
        # print(f"--- GÜN {day_idx} İŞLENİYOR ---")
        
        for machine in machines:
            machine_key = machine # Anahtarlar zaten motordan geldiği için uyumlu olmalı
            
            daily_jobs = []
            try:
                # Liste var mı?
                day_list = self.schedule_data.get(machine_key)
                if day_list and len(day_list) > day_idx:
                    daily_jobs = day_list[day_idx]
            except Exception as e:
                print(f"Hata ({machine}): {e}")
            
            if daily_jobs:
                has_any_job = True
                # print(f"   -> {machine}: {len(daily_jobs)} adet iş bulundu.")
                
                # KART OLUŞTUR
                card = QFrame()
                card.setStyleSheet(f"""
                    background-color: {Theme.SURFACE};
                    border: 1px solid {Theme.BORDER_LIGHT};
                    border-radius: {Theme.RADIUS_MD};
                """)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(20, 16, 20, 16)
                card_layout.setSpacing(12)

                # Başlık
                lbl_mach = QLabel(machine)
                lbl_mach.setStyleSheet(f"""
                    font-size: 16px;
                    font-weight: 600;
                    color: {Theme.TEXT_PRIMARY};
                    border-bottom: 1px solid {Theme.DIVIDER};
                    padding-bottom: 8px;
                """)
                card_layout.addWidget(lbl_mach)

                # Liste
                for job in daily_jobs:
                    job_code = job.get('code', 'Bilinmiyor')
                    job_cust = job.get('customer', '-')
                    job_m2 = job.get('m2', 0)

                    job_text = f"<b>{job_code}</b> - {job_cust} <span style='color:{Theme.TEXT_SECONDARY}'>({job_m2:.1f} m²)</span>"
                    lbl_job = QLabel(job_text)
                    lbl_job.setStyleSheet(f"""
                        color: {Theme.TEXT_PRIMARY};
                        font-size: 14px;
                        padding: 8px 0px;
                        border-bottom: 1px solid {Theme.DIVIDER};
                    """)
                    card_layout.addWidget(lbl_job)

                page_layout.addWidget(card)
        
        if not has_any_job:
            lbl_empty = QLabel("Bu tarih için planlanmış iş bulunamadı.")
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet(f"""
                color: {Theme.TEXT_DISABLED};
                font-size: 16px;
                font-weight: 500;
                margin-top: 50px;
            """)
            page_layout.addWidget(lbl_empty)
            
        page_layout.addStretch()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(scroll)
        
        return page

    def export_to_pdf(self):
        default_name = f"Haftalik_Plan_{datetime.now().strftime('%Y%m%d')}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Listeyi Kaydet", default_name, "PDF Files (*.pdf)")
        
        if not filename: return

        engine = PDFEngine(filename)
        
        success, msg = engine.generate_weekly_schedule_pdf(self.schedule_data)
        
        if success:
            QMessageBox.information(self, "Başarılı", f"Rapor kaydedildi:\n{filename}")
            try:
                import os
                os.startfile(filename)
            except:
                pass
        else:
            QMessageBox.critical(self, "Hata", f"PDF hatası:\n{msg}")