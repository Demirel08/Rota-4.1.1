"""
EFES ROTA X - Yonetici Dashboard
Excel temali, patron odakli tasarim

Patron icin kritik bilgiler:
- Geciken siparisler (KIRMIZI ALARM)
- Bugun teslim edilecekler
- Darbogazlar ve kapasite
- Gunluk/haftalik performans
- Fire oranlari
"""

import sys
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QStackedWidget, QButtonGroup, 
    QScrollArea, QGridLayout, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

try:
    from core.db_manager import db
except ImportError:
    db = None

# View importlari
try:
    from views.orders_view import OrdersView
except:
    OrdersView = None

try:
    from views.production_view import ProductionView
except:
    ProductionView = None

try:
    from views.planning_view import PlanningView
except:
    PlanningView = None

try:
    from views.stock_view import StockView
except:
    StockView = None

try:
    from views.report_view import ReportView
except:
    ReportView = None

try:
    from views.logs_view import LogsView
except:
    LogsView = None

try:
    from views.settings_view import SettingsView
except:
    SettingsView = None

try:
    from views.shipping_view import ShippingView
except:
    ShippingView = None

try:
    from views.decision_view import DecisionView
except:
    DecisionView = None


# =============================================================================
# EXCEL TEMASI
# =============================================================================
class Colors:
    BG = "#FFFFFF"
    HEADER_BG = "#F3F3F3"
    BORDER = "#D4D4D4"
    GRID = "#E0E0E0"
    TEXT = "#1A1A1A"
    TEXT_SECONDARY = "#666666"
    TEXT_MUTED = "#999999"
    SELECTION = "#B4D7FF"
    ACCENT = "#217346"
    ROW_ALT = "#F9F9F9"
    
    SIDEBAR_BG = "#1E3A2F"
    SIDEBAR_TEXT = "#FFFFFF"
    SIDEBAR_HOVER = "#2D5A47"
    SIDEBAR_ACTIVE = "#217346"
    
    CRITICAL = "#C00000"
    CRITICAL_BG = "#FDE8E8"
    WARNING = "#C65911"
    WARNING_BG = "#FFF3E0"
    SUCCESS = "#107C41"
    SUCCESS_BG = "#E6F4EA"
    INFO = "#0066CC"
    INFO_BG = "#E3F2FD"


# =============================================================================
# METRIK KARTI
# =============================================================================
class MetricCard(QFrame):
    """Buyuk metrik karti"""
    
    def __init__(self, title, value, subtitle="", color=Colors.TEXT, icon=""):
        super().__init__()
        self.color = color
        self.setup_ui(title, value, subtitle, icon)
    
    def setup_ui(self, title, value, subtitle, icon):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        
        # Baslik
        header = QHBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-weight: 500;")
        header.addWidget(lbl_title)
        
        header.addStretch()
        
        if icon:
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet(f"font-size: 14px;")
            header.addWidget(lbl_icon)
        
        layout.addLayout(header)
        
        # Deger
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: {self.color};
        """)
        layout.addWidget(self.lbl_value)
        
        # Alt yazi
        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_SECONDARY};")
            layout.addWidget(self.lbl_subtitle)
        else:
            self.lbl_subtitle = None
    
    def set_value(self, value, subtitle=None):
        self.lbl_value.setText(str(value))
        if subtitle and self.lbl_subtitle:
            self.lbl_subtitle.setText(subtitle)


# =============================================================================
# UYARI KARTI
# =============================================================================
class AlertCard(QFrame):
    """Kritik uyari karti"""
    
    def __init__(self, alert_type="warning"):
        super().__init__()
        self.alert_type = alert_type
        self.items = []
        self.setup_ui()
    
    def setup_ui(self):
        if self.alert_type == "critical":
            bg = Colors.CRITICAL_BG
            border = Colors.CRITICAL
            icon = "🚨"
            title = "Geciken Siparisler"
        elif self.alert_type == "warning":
            bg = Colors.WARNING_BG
            border = Colors.WARNING
            icon = "⚠️"
            title = "Bugun Teslim"
        else:
            bg = Colors.INFO_BG
            border = Colors.INFO
            icon = "ℹ️"
            title = "Bilgi"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        
        # Baslik
        header = QHBoxLayout()
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 16px;")
        header.addWidget(lbl_icon)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {border};")
        header.addWidget(self.lbl_title)
        
        header.addStretch()
        
        self.lbl_count = QLabel("0")
        self.lbl_count.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: white;
            background-color: {border};
            padding: 2px 8px;
            border-radius: 10px;
        """)
        header.addWidget(self.lbl_count)
        
        layout.addLayout(header)
        
        # Liste alani
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(4)
        layout.addLayout(self.list_layout)
    
    def set_items(self, items):
        """Listeyi guncelle"""
        self.items = items
        self.lbl_count.setText(str(len(items)))
        
        # Mevcut itemlari temizle
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Yeni itemlari ekle (max 5)
        for item in items[:5]:
            row = QLabel(f"• {item}")
            row.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT}; padding-left: 4px;")
            row.setWordWrap(True)
            self.list_layout.addWidget(row)
        
        if len(items) > 5:
            more = QLabel(f"... ve {len(items) - 5} siparis daha")
            more.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED}; padding-left: 4px;")
            self.list_layout.addWidget(more)


# =============================================================================
# KAPASITE CUBUGU
# =============================================================================
class CapacityBar(QFrame):
    """Istasyon kapasite cubugu"""
    
    def __init__(self, name, percent, status="Normal"):
        super().__init__()
        self.setup_ui(name, percent, status)
    
    def setup_ui(self, name, percent, status):
        self.setFixedHeight(32)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Istasyon adi
        lbl_name = QLabel(name)
        lbl_name.setFixedWidth(100)
        lbl_name.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Colors.TEXT};")
        layout.addWidget(lbl_name)
        
        # Progress bar
        bar = QProgressBar()
        bar.setFixedHeight(8)
        bar.setValue(min(percent, 100))
        bar.setTextVisible(False)
        
        if status == "Kritik" or percent > 90:
            bar_color = Colors.CRITICAL
        elif status == "Yogun" or percent > 70:
            bar_color = Colors.WARNING
        else:
            bar_color = Colors.SUCCESS
        
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.GRID};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(bar, 1)
        
        # Yuzde
        lbl_pct = QLabel(f"%{percent}")
        lbl_pct.setFixedWidth(45)
        lbl_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_pct.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {bar_color};")
        layout.addWidget(lbl_pct)
        
        # Durum
        lbl_status = QLabel(status)
        lbl_status.setFixedWidth(50)
        lbl_status.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(lbl_status)


# =============================================================================
# MINI TABLO
# =============================================================================
class MiniTable(QFrame):
    """Kucuk veri tablosu"""
    
    def __init__(self, title, headers):
        super().__init__()
        self.headers = headers
        self.setup_ui(title)
    
    def setup_ui(self, title):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        
        # Baslik
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {Colors.TEXT};")
        layout.addWidget(lbl_title)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        for h in self.headers:
            lbl = QLabel(h)
            lbl.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED}; font-weight: bold;")
            header_layout.addWidget(lbl, 1)
        layout.addLayout(header_layout)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep)
        
        # Veri alani
        self.data_layout = QVBoxLayout()
        self.data_layout.setSpacing(6)
        layout.addLayout(self.data_layout)
    
    def set_data(self, rows):
        """Veriyi guncelle"""
        while self.data_layout.count():
            item = self.data_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        
        for row_data in rows[:8]:  # Max 8 satir
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            
            for i, cell in enumerate(row_data):
                lbl = QLabel(str(cell))
                lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT};")
                row_layout.addWidget(lbl, 1)
            
            self.data_layout.addLayout(row_layout)


# =============================================================================
# ANA DASHBOARD
# =============================================================================
class DashboardView(QWidget):
    logout_signal = Signal()
    
    def __init__(self, user_data):
        super().__init__()
        self.user = user_data
        self.setup_ui()
        
        # Canli yenileme (5 saniye)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(5000)
    
    def setup_ui(self):
        self.setStyleSheet(f"background-color: {Colors.HEADER_BG};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === SIDEBAR ===
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # === ICERIK ALANI ===
        content = QWidget()
        content.setStyleSheet(f"background-color: {Colors.HEADER_BG};")
        
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sayfa yoneticisi
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)
        
        # Sayfalari yukle
        self._load_pages()
        
        main_layout.addWidget(content, 1)
        
        # Ilk sayfayi ac
        self.menu_group.button(0).click()
    
    def _create_sidebar(self):
        """Sol menu"""
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SIDEBAR_BG};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(4)
        
        # Logo
        lbl_logo = QLabel("EFES ROTA")
        lbl_logo.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {Colors.SIDEBAR_TEXT};
            padding-bottom: 4px;
        """)
        layout.addWidget(lbl_logo)
        
        # Kullanici
        lbl_user = QLabel(self.user.get('full_name', 'Admin').upper())
        lbl_user.setStyleSheet(f"""
            font-size: 10px;
            color: {Colors.TEXT_MUTED};
            letter-spacing: 1px;
            padding-bottom: 20px;
        """)
        layout.addWidget(lbl_user)
        
        # Menu grubbu
        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)
        
        # Menu butonlari
        menu_items = [
            ("Genel Bakis", 0),
            ("Siparisler", 1),
            ("Uretim Takip", 2),
            ("Is Yuku (Gantt)", 3),
            ("Stok Depo", 4),
            ("Sevkiyat", 5),
            ("Raporlama", 6),
            ("Islem Gecmisi", 7),
            ("Ayarlar", 8),
            ("Karar Destek", 9),
        ]
        
        for text, idx in menu_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.SIDEBAR_TEXT};
                    text-align: left;
                    padding: 10px 12px;
                    font-size: 12px;
                    font-weight: 500;
                    border: none;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.SIDEBAR_HOVER};
                }}
                QPushButton:checked {{
                    background-color: {Colors.SIDEBAR_ACTIVE};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda checked, i=idx: self.stack.setCurrentIndex(i))
            self.menu_group.addButton(btn, idx)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Cikis butonu
        btn_logout = QPushButton("Oturumu Kapat")
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                text-align: left;
                padding: 10px 12px;
                font-size: 11px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {Colors.CRITICAL};
                background-color: rgba(192, 0, 0, 0.1);
            }}
        """)
        btn_logout.clicked.connect(self.logout_signal.emit)
        layout.addWidget(btn_logout)
        
        return sidebar
    
    def _load_pages(self):
        """Sayfalari yukle"""
        # 0. Dashboard
        self.dashboard_page = QWidget()
        self._setup_dashboard_page()
        self.stack.addWidget(self.dashboard_page)
        
        # 1. Siparisler
        if OrdersView:
            self.stack.addWidget(OrdersView())
        else:
            self.stack.addWidget(self._placeholder("Siparisler"))
        
        # 2. Uretim Takip
        if ProductionView:
            self.stack.addWidget(ProductionView())
        else:
            self.stack.addWidget(self._placeholder("Uretim Takip"))
        
        # 3. Planlama
        if PlanningView:
            self.stack.addWidget(PlanningView())
        else:
            self.stack.addWidget(self._placeholder("Is Yuku"))
        
        # 4. Stok
        if StockView:
            self.stack.addWidget(StockView())
        else:
            self.stack.addWidget(self._placeholder("Stok"))
        
        # 5. Sevkiyat
        if ShippingView:
            self.stack.addWidget(ShippingView())
        else:
            self.stack.addWidget(self._placeholder("Sevkiyat"))
        
        # 6. Raporlar
        if ReportView:
            self.stack.addWidget(ReportView())
        else:
            self.stack.addWidget(self._placeholder("Raporlama"))
        
        # 7. Loglar
        if LogsView:
            self.stack.addWidget(LogsView())
        else:
            self.stack.addWidget(self._placeholder("Islem Gecmisi"))
        
        # 8. Ayarlar
        if SettingsView:
            self.stack.addWidget(SettingsView())
        else:
            self.stack.addWidget(self._placeholder("Ayarlar"))
        
        # 9. Karar Destek
        if DecisionView:
            self.stack.addWidget(DecisionView())
        else:
            self.stack.addWidget(self._placeholder("Karar Destek"))
    
    def _placeholder(self, name):
        """Placeholder sayfa"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        
        lbl = QLabel(f"{name} modulu yuklenemedi")
        lbl.setStyleSheet(f"font-size: 16px; color: {Colors.TEXT_MUTED};")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        return w
    
    def _setup_dashboard_page(self):
        """Dashboard sayfasini olustur"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background-color: {Colors.HEADER_BG};")
        
        content = QWidget()
        content.setStyleSheet(f"background-color: {Colors.HEADER_BG};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        # Baslik
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        lbl_title = QLabel("Genel Bakis")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.TEXT};")
        title_layout.addWidget(lbl_title)
        
        self.lbl_time = QLabel(datetime.now().strftime("Son guncelleme: %H:%M:%S"))
        self.lbl_time.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        title_layout.addWidget(self.lbl_time)
        
        header.addLayout(title_layout)
        header.addStretch()
        
        # Yenile butonu
        btn_refresh = QPushButton("Yenile")
        btn_refresh.setFixedHeight(32)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.update_dashboard)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1D6640;
            }}
        """)
        header.addWidget(btn_refresh)
        
        layout.addLayout(header)
        
        # === KRITIK UYARILAR ===
        alerts_layout = QHBoxLayout()
        alerts_layout.setSpacing(16)
        
        self.alert_overdue = AlertCard("critical")
        alerts_layout.addWidget(self.alert_overdue, 1)
        
        self.alert_today = AlertCard("warning")
        alerts_layout.addWidget(self.alert_today, 1)
        
        layout.addLayout(alerts_layout)
        
        # === ANA METRIKLER ===
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        
        self.metric_active = MetricCard("Aktif Siparisler", "0", "Beklemede + Uretimde", Colors.INFO, "📦")
        self.metric_today_done = MetricCard("Bugun Tamamlanan", "0", "Adet", Colors.SUCCESS, "✓")
        self.metric_urgent = MetricCard("Acil / Kritik", "0", "Oncelikli isler", Colors.WARNING, "⚡")
        self.metric_fire = MetricCard("Fire / Hata", "0", "Toplam", Colors.CRITICAL, "🔥")
        
        metrics_layout.addWidget(self.metric_active, 1)
        metrics_layout.addWidget(self.metric_today_done, 1)
        metrics_layout.addWidget(self.metric_urgent, 1)
        metrics_layout.addWidget(self.metric_fire, 1)
        
        layout.addLayout(metrics_layout)
        
        # === IKINCI SATIR METRIKLER ===
        metrics2_layout = QHBoxLayout()
        metrics2_layout.setSpacing(16)
        
        self.metric_waiting = MetricCard("Beklemede", "0", "Uretim bekleniyor", Colors.TEXT_SECONDARY, "⏳")
        self.metric_production = MetricCard("Uretimde", "0", "Aktif uretim", Colors.INFO, "🔧")
        self.metric_completed = MetricCard("Tamamlandi", "0", "Sevke hazir", Colors.SUCCESS, "📋")
        self.metric_shipped = MetricCard("Sevk Edildi", "0", "Bu ay", Colors.TEXT_MUTED, "🚚")
        
        metrics2_layout.addWidget(self.metric_waiting, 1)
        metrics2_layout.addWidget(self.metric_production, 1)
        metrics2_layout.addWidget(self.metric_completed, 1)
        metrics2_layout.addWidget(self.metric_shipped, 1)
        
        layout.addLayout(metrics2_layout)
        
        # === ALT KISIM: DARBOGAZLAR + TABLOLAR ===
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)
        
        # Sol: Darbogaz analizi
        bottleneck_frame = QFrame()
        bottleneck_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        bottleneck_layout = QVBoxLayout(bottleneck_frame)
        bottleneck_layout.setContentsMargins(16, 14, 16, 14)
        bottleneck_layout.setSpacing(12)
        
        # Baslik
        bottleneck_header = QHBoxLayout()
        lbl_bottleneck = QLabel("Istasyon Doluluk Orani")
        lbl_bottleneck.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT};")
        bottleneck_header.addWidget(lbl_bottleneck)
        bottleneck_header.addStretch()
        
        # Renk aciklamasi
        legend = QHBoxLayout()
        legend.setSpacing(12)
        for color, text in [(Colors.CRITICAL, "Kritik"), (Colors.WARNING, "Yogun"), (Colors.SUCCESS, "Normal")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"font-size: 10px; color: {color};")
            legend.addWidget(dot)
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 10px; color: {Colors.TEXT_MUTED};")
            legend.addWidget(lbl)
        bottleneck_header.addLayout(legend)
        
        bottleneck_layout.addLayout(bottleneck_header)
        
        # Cubuklar alani
        self.capacity_layout = QVBoxLayout()
        self.capacity_layout.setSpacing(8)
        bottleneck_layout.addLayout(self.capacity_layout)
        
        bottom_layout.addWidget(bottleneck_frame, 2)
        
        # Sag: Tablolar
        tables_layout = QVBoxLayout()
        tables_layout.setSpacing(16)
        
        # En yogun musteriler
        self.table_customers = MiniTable("En Cok Siparis Veren", ["Musteri", "Siparis", "m²"])
        tables_layout.addWidget(self.table_customers)
        
        # Gunluk ozet
        self.table_daily = MiniTable("Son 7 Gun Ozeti", ["Gun", "Tamamlanan", "Fire"])
        tables_layout.addWidget(self.table_daily)
        
        bottom_layout.addLayout(tables_layout, 1)
        
        layout.addLayout(bottom_layout)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        page_layout = QVBoxLayout(self.dashboard_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        
        # Ilk yukleme
        self.update_dashboard()
    
    def update_dashboard(self):
        """Dashboard verilerini guncelle"""
        if not db:
            return
        
        try:
            self.lbl_time.setText(datetime.now().strftime("Son guncelleme: %H:%M:%S"))
            
            # === TEMEL ISTATISTIKLER ===
            stats = db.get_dashboard_stats()
            self.metric_active.set_value(stats.get('active', 0))
            self.metric_urgent.set_value(stats.get('urgent', 0))
            self.metric_fire.set_value(stats.get('fire', 0))
            
            # === DETAYLI DURUM SAYILARI ===
            all_orders = db.get_all_orders()
            
            beklemede = sum(1 for o in all_orders if o.get('status') == 'Beklemede')
            uretimde = sum(1 for o in all_orders if o.get('status') == 'Üretimde')
            tamamlandi = sum(1 for o in all_orders if o.get('status') == 'Tamamlandı')
            sevk_edildi = sum(1 for o in all_orders if o.get('status') == 'Sevk Edildi')
            
            self.metric_waiting.set_value(beklemede)
            self.metric_production.set_value(uretimde)
            self.metric_completed.set_value(tamamlandi)
            self.metric_shipped.set_value(sevk_edildi)
            self.metric_today_done.set_value(tamamlandi)  # Simdilik toplam
            
            # === GECIKEN SIPARISLER ===
            today = datetime.now().date()
            overdue = []
            today_delivery = []
            
            for o in all_orders:
                if o.get('status') in ['Sevk Edildi', 'Tamamlandı']:
                    continue
                
                delivery = o.get('delivery_date')
                if delivery:
                    try:
                        if isinstance(delivery, str):
                            d_date = datetime.strptime(delivery, '%Y-%m-%d').date()
                        else:
                            d_date = delivery
                        
                        if d_date < today:
                            days_late = (today - d_date).days
                            overdue.append(f"{o['order_code']} - {o['customer_name']} ({days_late} gun gecikti)")
                        elif d_date == today:
                            today_delivery.append(f"{o['order_code']} - {o['customer_name']}")
                    except:
                        pass
            
            self.alert_overdue.set_items(overdue)
            self.alert_today.set_items(today_delivery)
            
            # === KAPASITE CUBUKLARI ===
            while self.capacity_layout.count():
                item = self.capacity_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            station_loads = db.get_station_loads()
            for station in station_loads:
                bar = CapacityBar(station['name'], station['percent'], station['status'])
                self.capacity_layout.addWidget(bar)
            
            # === MUSTERI TABLOSU ===
            customer_stats = {}
            for o in all_orders:
                if o.get('status') == 'Sevk Edildi':
                    continue
                cust = o.get('customer_name', 'Bilinmiyor')
                m2 = o.get('declared_total_m2', 0) or 0
                if cust not in customer_stats:
                    customer_stats[cust] = {'count': 0, 'm2': 0}
                customer_stats[cust]['count'] += 1
                customer_stats[cust]['m2'] += m2
            
            sorted_customers = sorted(customer_stats.items(), key=lambda x: x[1]['count'], reverse=True)
            customer_rows = [(c, str(v['count']), f"{v['m2']:.0f}") for c, v in sorted_customers[:5]]
            self.table_customers.set_data(customer_rows)
            
            # === GUNLUK OZET ===
            # Simdilik statik veri
            daily_rows = [
                ("Bugun", str(tamamlandi), str(stats.get('fire', 0))),
                ("Dun", "-", "-"),
                ("2 gun once", "-", "-"),
            ]
            self.table_daily.set_data(daily_rows)
            
        except Exception as e:
            print(f"Dashboard guncelleme hatasi: {e}")
            import traceback
            traceback.print_exc()


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    
    window = DashboardView({"full_name": "Test Admin", "role": "admin"})
    window.setWindowTitle("EFES ROTA X - Dashboard")
    window.resize(1400, 800)
    window.show()
    
    sys.exit(app.exec())