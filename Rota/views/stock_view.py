import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QPushButton, QAbstractItemView, QInputDialog, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

try:
    from core.db_manager import db
    from ui.theme import Theme
except ImportError:
    pass

class StockView(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # BAŞLIK VE BUTONLAR
        header = QHBoxLayout()
        
        title_box = QVBoxLayout()
        title = QLabel("STOK YÖNETİMİ (HAMMADDE)")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Theme.TEXT_DARK};")
        sub = QLabel("Depodaki cam miktarları ve kritik seviye kontrolü")
        sub.setStyleSheet("color: #7F8C8D; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        
        header.addStretch()
        
        btn_add = QPushButton("➕ STOK GİRİŞİ YAP")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_stock_dialog)
        btn_add.setStyleSheet("""
            QPushButton { background-color: #27AE60; color: white; border-radius: 6px; padding: 10px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #2ECC71; }
        """)
        header.addWidget(btn_add)
        
        btn_refresh = QPushButton("⟳ YENİLE")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_data)
        btn_refresh.setStyleSheet("""
            QPushButton { background-color: white; border: 1px solid #ccc; border-radius: 6px; padding: 10px 15px; color: #333; font-weight: bold; }
            QPushButton:hover { background-color: #f5f5f5; }
        """)
        header.addWidget(btn_refresh)
        
        layout.addLayout(header)

        # STOK TABLOSU
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ÜRÜN ADI", "MEVCUT (m²)", "DOLULUK", "DURUM"])
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        
        header_obj = self.table.horizontalHeader()
        header_obj.setSectionResizeMode(QHeaderView.Stretch)
        header_obj.setStyleSheet("QHeaderView::section { background-color: #ECF0F1; color: #2C3E50; padding: 10px; border: none; border-bottom: 2px solid #BDC3C7; font-weight: bold; }")
        
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #BDC3C7; background-color: white; font-size: 14px; }
            QTableWidget::item { border-bottom: 1px solid #F0F0F0; padding-left: 10px; }
        """)
        
        layout.addWidget(self.table)

    def refresh_data(self):
        """Stok verilerini çek"""
        self.table.setRowCount(0)
        stocks = db.get_all_stocks()
        
        self.table.setRowCount(len(stocks))
        
        for row_idx, item in enumerate(stocks):
            qty = item['quantity_m2']
            limit = item['min_limit']
            name = item['product_name']
            
            # 1. Ürün Adı
            cell_name = QTableWidgetItem(name)
            cell_name.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.table.setItem(row_idx, 0, cell_name)
            
            # 2. Miktar
            cell_qty = QTableWidgetItem(f"{qty:.2f} m²")
            cell_qty.setTextAlignment(Qt.AlignCenter)
            cell_qty.setFont(QFont("Consolas", 12))
            
            if qty <= 0: cell_qty.setForeground(QColor("#C0392B")) # Kırmızı
            elif qty < limit: cell_qty.setForeground(QColor("#E67E22")) # Turuncu
            else: cell_qty.setForeground(QColor("#27AE60")) # Yeşil
            
            self.table.setItem(row_idx, 1, cell_qty)
            
            # 3. Görsel Bar
            max_cap = limit * 5 
            percent = int((qty / max_cap) * 100) if qty > 0 else 0
            percent = min(percent, 100)
            
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(percent)
            pbar.setTextVisible(False)
            pbar.setFixedHeight(12)
            
            bar_color = "#27AE60"
            if qty < limit: bar_color = "#E67E22"
            if qty <= 0: bar_color = "#C0392B"
            
            pbar.setStyleSheet(f"""
                QProgressBar {{ border: none; background-color: #ECF0F1; border-radius: 6px; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 6px; }}
            """)
            
            w = QWidget()
            l = QVBoxLayout(w)
            l.addWidget(pbar)
            l.setAlignment(Qt.AlignCenter)
            l.setContentsMargins(10, 0, 10, 0)
            self.table.setCellWidget(row_idx, 2, w)
            
            # 4. Uyarı Mesajı
            status_text = "YETERLİ"
            status_color = "#27AE60"
            
            if qty <= 0:
                status_text = "TÜKENDİ!"
                status_color = "#C0392B"
            elif qty < limit:
                status_text = "AZALDI"
                status_color = "#E67E22"
            
            cell_status = QTableWidgetItem(status_text)
            cell_status.setTextAlignment(Qt.AlignCenter)
            cell_status.setForeground(QColor("white"))
            cell_status.setBackground(QColor(status_color))
            cell_status.setFont(QFont("Arial", 10, QFont.Bold))
            self.table.setItem(row_idx, 3, cell_status)

    def add_stock_dialog(self):
        """Hızlı stok ekleme"""
        # Mevcut ürünleri listele
        stocks = db.get_all_stocks()
        items = [s['product_name'] for s in stocks]
        
        if not items:
            items = ["4mm Düz Cam", "6mm Düz Cam"] # Varsayılan
            
        item, ok = QInputDialog.getItem(self, "Stok Girişi", "Hangi cama ekleme yapılacak?", items, 0, False)
        
        if ok and item:
            qty, ok2 = QInputDialog.getDouble(self, "Miktar (m²)", f"{item} için kaç m² eklenecek?", 100, 0, 10000, 1)
            if ok2:
                db.add_stock(item, qty)
                QMessageBox.information(self, "Başarılı", f"{qty} m² {item} depoya eklendi.")
                self.refresh_data()