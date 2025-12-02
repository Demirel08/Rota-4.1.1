import sys
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QPushButton, QAbstractItemView, QStyledItemDelegate, 
                               QDialog, QListWidget, QMessageBox, QStyle)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QBrush

try:
    from ui.theme import Theme
    from core.smart_planner import planner 
    try:
        from views.weekly_schedule_dialog import WeeklyScheduleView
    except ImportError:
        WeeklyScheduleView = None
except ImportError:
    pass

# --- ÖZEL BOYACI SINIFI (DELEGATE) ---
class GanttDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        bg_color = index.data(Qt.UserRole)      
        text_color = index.data(Qt.UserRole + 1) 
        text = index.data(Qt.DisplayRole)        

        painter.save()
        if bg_color:
            painter.fillRect(option.rect, bg_color)
        else:
            painter.fillRect(option.rect, QColor(Theme.SURFACE))

        if option.state & QStyle.State_Selected:
            pen = painter.pen()
            pen.setColor(QColor(Theme.PRIMARY))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(1,1,-1,-1))

        if text:
            painter.setPen(text_color if text_color else Qt.black)
            
            lines = text.split('\n')
            
            # Yüzde Fontu
            font_percent = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font_percent)
            
            rect = option.rect
            
            if len(lines) > 1:
                # Üst Satır: Yüzde
                painter.drawText(rect.adjusted(0, -8, 0, 0), Qt.AlignCenter, lines[0])
                
                # Alt Satır: m2 (Daha küçük)
                font_m2 = QFont("Segoe UI", 8)
                painter.setFont(font_m2)

                # Eğer zemin koyu ise yazıyı beyaz yap, yoksa gri
                if bg_color and bg_color.name() in [Theme.DANGER, Theme.WARNING, Theme.SUCCESS]:
                     painter.setPen(QColor("white"))
                else:
                     painter.setPen(QColor(Theme.TEXT_SECONDARY))
                     
                painter.drawText(rect.adjusted(0, 10, 0, 0), Qt.AlignCenter, lines[1])
            else:
                painter.drawText(rect, Qt.AlignCenter, text)

        painter.restore()

# --- DETAY PENCERESİ ---
class DayDetailDialog(QDialog):
    def __init__(self, station, date_str, orders, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"İş Listesi: {station}")
        self.setFixedSize(500, 600)
        self.setStyleSheet(f"background-color: {Theme.BACKGROUND};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Başlık
        title = QLabel(station)
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 600;
            color: {Theme.TEXT_PRIMARY};
        """)
        layout.addWidget(title)

        # Alt başlık
        sub = QLabel(f"Tarih: {date_str}")
        sub.setStyleSheet(f"""
            font-size: 14px;
            color: {Theme.TEXT_SECONDARY};
        """)
        layout.addWidget(sub)

        # Liste
        lst = QListWidget()
        lst.setStyleSheet(f"""
            QListWidget {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Theme.RADIUS_MD};
                font-size: 14px;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 14px;
                border-bottom: 1px solid {Theme.DIVIDER};
                color: {Theme.TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background-color: {Theme.SURFACE_DARK};
            }}
            QListWidget::item:selected {{
                background-color: rgba(38, 166, 154, 0.1);
                color: {Theme.TEXT_PRIMARY};
            }}
        """)

        if not orders:
            lst.addItem("Bu tarih için planlanmış iş bulunamadı.")
        else:
            for order in orders:
                text = f"{order['code']} - {order['customer']} ({order['m2']:.1f} m²)"
                lst.addItem(text)
        layout.addWidget(lst)

        # Kapat butonu
        btn = QPushButton("KAPAT")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.accept)
        btn.setFixedHeight(44)
        btn.setStyleSheet(f"""
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
        layout.addWidget(btn)

# --- ANA EKRAN ---
class PlanningView(QWidget):
    def __init__(self):
        super().__init__()
        
        self.machines = [
            "INTERMAC", "LIVA KESIM", "LAMINE KESIM",
            "CNC RODAJ", "DOUBLEDGER", "ZIMPARA",
            "TESIR A1", "TESIR B1", "TESIR B1-1", "TESIR B1-2",
            "DELİK", "OYGU",
            "TEMPER A1", "TEMPER B1", "TEMPER BOMBE",
            "LAMINE A1", "ISICAM B1",
            "SEVKİYAT"
        ]
        
        self.DAYS_RANGE = 30 
        self.cached_details = {}
        
        self.setup_ui()
        self.init_table_structure()
        self.table.setItemDelegate(GanttDelegate())
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plan)
        self.timer.start(5000) 
        self.refresh_plan()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("İş Yükü Planlama")
        title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 600;
            color: {Theme.TEXT_PRIMARY};
        """)

        sub_title = QLabel("Kutulara tıklayarak iş listesini görüntüleyin")
        sub_title.setStyleSheet(f"""
            color: {Theme.TEXT_SECONDARY};
            font-size: 14px;
        """)

        title_box.addWidget(title)
        title_box.addWidget(sub_title)
        header.addLayout(title_box)
        header.addStretch()

        try:
            btn_list = QPushButton("HAFTALIK LISTE")
            btn_list.setCursor(Qt.PointingHandCursor)
            btn_list.clicked.connect(self.open_weekly_schedule)
            btn_list.setFixedHeight(40)
            btn_list.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.SURFACE};
                    color: {Theme.TEXT_PRIMARY};
                    border: 1px solid {Theme.BORDER};
                    border-radius: {Theme.RADIUS_SM};
                    padding: 0 20px;
                    font-weight: 500;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.SURFACE_DARK};
                    border-color: {Theme.PRIMARY};
                }}
            """)
            header.addWidget(btn_list)
        except: pass

        btn_refresh = QPushButton("GUNCELLE")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_plan)
        btn_refresh.setFixedHeight(40)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: white;
                border: none;
                border-radius: {Theme.RADIUS_SM};
                padding: 0 24px;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_DARK};
            }}
        """)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.cellClicked.connect(self.on_cell_clicked)
        layout.addWidget(self.table)
        
        legend = QHBoxLayout()
        legend.setSpacing(12)
        legend.addStretch()
        self.add_legend_item(legend, Theme.SURFACE, "BOŞ", Theme.BORDER)
        self.add_legend_item(legend, Theme.SUCCESS, "NORMAL")
        self.add_legend_item(legend, Theme.WARNING, "YOĞUN")
        self.add_legend_item(legend, Theme.DANGER, "DOLU")
        layout.addLayout(legend)

    def add_legend_item(self, layout, bg_color, text, border_color=None):
        lbl = QLabel(text)
        text_color = Theme.TEXT_PRIMARY if border_color else "white"
        style = f"""
            background-color: {bg_color};
            color: {text_color};
            font-weight: 500;
            border-radius: {Theme.RADIUS_SM};
            padding: 8px 16px;
            font-size: 12px;
        """
        if border_color:
            style += f"border: 1px solid {border_color};"
        lbl.setStyleSheet(style)
        layout.addWidget(lbl)

    def open_weekly_schedule(self):
        if WeeklyScheduleView:
            dialog = WeeklyScheduleView(self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Hata", "Haftalık Liste modülü yüklenemedi.")

    def init_table_structure(self):
        columns = ["İSTASYON"]
        today = datetime.now()
        tr_days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        for i in range(self.DAYS_RANGE):
            day_date = today + timedelta(days=i)
            columns.append(f"{day_date.strftime('%d.%m')}\n{tr_days[day_date.weekday()]}")
            
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(self.machines))
        
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setShowGrid(True)
        
        header_obj = self.table.horizontalHeader()
        header_obj.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 200)
        for i in range(1, self.DAYS_RANGE + 1):
            header_obj.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, 70)

        header_obj.setStyleSheet(f"""
            background-color: {Theme.SURFACE_DARK};
            color: {Theme.TEXT_SECONDARY};
            font-weight: 600;
            font-size: 12px;
            padding: 14px 16px;
            border: none;
            border-bottom: 1px solid {Theme.DIVIDER};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.BORDER_LIGHT};
                gridline-color: {Theme.DIVIDER};
                border-radius: {Theme.RADIUS_MD};
            }}
        """)

        for row_idx, machine_name in enumerate(self.machines):
            item = QTableWidgetItem(machine_name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.ItemIsEnabled)
            item.setData(Qt.UserRole, QColor(Theme.SURFACE_DARK))
            item.setData(Qt.UserRole + 1, QColor(Theme.TEXT_PRIMARY))
            item.setData(Qt.DisplayRole, machine_name)
            self.table.setItem(row_idx, 0, item)

    def refresh_plan(self):
        if 'planner' not in globals() or planner is None: return

        try:
            result = planner.calculate_forecast()
            if isinstance(result, tuple) and len(result) >= 3:
                forecast, details, loads = result
                self.cached_details = details
            else:
                return
        except: return

        for row_idx, machine_name in enumerate(self.machines):
            machine_key = machine_name.upper()
            daily_percents = forecast.get(machine_key, [0]*self.DAYS_RANGE)
            daily_loads = loads.get(machine_key, [0]*self.DAYS_RANGE)
            
            capacity = planner.capacities.get(machine_key, 1000)

            if len(daily_percents) < self.DAYS_RANGE:
                daily_percents += [0] * (self.DAYS_RANGE - len(daily_percents))
            
            for day_idx, percent in enumerate(daily_percents):
                col_idx = day_idx + 1 
                
                current_load = daily_loads[day_idx]
                if percent > 0:
                    # --- DÜZELTME BURADA: int() ile tam sayıya yuvarlıyoruz ---
                    text = f"%{int(percent)}\n{int(current_load)}/{int(capacity)} m²"
                else:
                    text = "-"
                
                item = self.table.item(row_idx, col_idx)
                if not item:
                    item = QTableWidgetItem()
                    self.table.setItem(row_idx, col_idx, item)
                
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) 
                item.setData(Qt.DisplayRole, text)
                
                bg_color = QColor(Theme.SURFACE)
                text_color = QColor(Theme.TEXT_DISABLED)

                if percent > 0:
                    text_color = QColor("white")
                    if percent < 50: bg_color = QColor(Theme.SUCCESS)
                    elif percent < 90: bg_color = QColor(Theme.WARNING)
                    else: bg_color = QColor(Theme.DANGER)
                
                item.setData(Qt.UserRole, bg_color)
                item.setData(Qt.UserRole + 1, text_color)

    def on_cell_clicked(self, row, col):
        if col == 0: return
        day_idx = col - 1
        machine_name = self.machines[row]
        machine_key = machine_name.upper()
        if machine_key in self.cached_details:
            try:
                orders = self.cached_details[machine_key][day_idx]
                today = datetime.now()
                target_date = today + timedelta(days=day_idx)
                dialog = DayDetailDialog(machine_name, target_date.strftime("%d.%m.%Y"), orders, self)
                dialog.exec()
            except: pass