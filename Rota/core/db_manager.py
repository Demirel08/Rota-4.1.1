import sqlite3
import hashlib
import os
from contextlib import contextmanager
from datetime import datetime

# === YENİ: GÜVENLİK VE LOGLAMA ===
try:
    from core.security import password_manager
    from core.logger import logger
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


class DatabaseManager:
    """
    EFES ROTA X - Merkezi Veritabanı Yöneticisi
    GÜNCELLENMİŞ SÜRÜM - Güvenlik + Loglama + Tüm Metodlar ✅
    """
    
    def __init__(self, db_name="efes_factory.db"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_name)
        
        self.init_database()
        self.create_default_users() 
        self.init_default_stocks()
        self.init_machine_capacities()
        self.init_default_prices()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ Veritabanı Hatası: {e}")
            if SECURITY_AVAILABLE:
                logger.error(f"Veritabanı Hatası: {e}")
            raise e
        finally:
            conn.close()

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. KULLANICILAR
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, full_name TEXT, station_name TEXT)""")

            # 2. SİPARİŞLER
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_code TEXT NOT NULL, 
                    barcode TEXT,
                    customer_name TEXT,
                    product_type TEXT,
                    thickness INTEGER,
                    width REAL,
                    height REAL,
                    quantity INTEGER NOT NULL,
                    declared_total_m2 REAL DEFAULT 0,
                    route TEXT, 
                    sale_price REAL DEFAULT 0,
                    total_price REAL DEFAULT 0,
                    calculated_cost REAL DEFAULT 0,
                    profit REAL DEFAULT 0,
                    currency TEXT DEFAULT 'TL',
                    status TEXT DEFAULT 'Beklemede',
                    priority TEXT DEFAULT 'Normal',
                    has_breakage INTEGER DEFAULT 0,
                    rework_count INTEGER DEFAULT 0,
                    pallet_id INTEGER,
                    delivery_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. LOGLAR
            cursor.execute("""CREATE TABLE IF NOT EXISTS production_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, station_name TEXT, action TEXT, quantity INTEGER, operator_name TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(order_id) REFERENCES orders(id))""")
            
            # 4. STOK
            cursor.execute("""CREATE TABLE IF NOT EXISTS stocks (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT UNIQUE, quantity_m2 REAL DEFAULT 0, min_limit REAL DEFAULT 100, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            
            # 5. AYARLAR
            cursor.execute("""CREATE TABLE IF NOT EXISTS factory_settings (setting_key TEXT UNIQUE, setting_value REAL DEFAULT 0)""")
            
            # 6. FİYATLAR
            cursor.execute("""CREATE TABLE IF NOT EXISTS unit_prices (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT UNIQUE, price_per_m2 REAL DEFAULT 0, category TEXT)""")
            
            # 7. SEVKİYAT
            cursor.execute("""CREATE TABLE IF NOT EXISTS shipments (id INTEGER PRIMARY KEY AUTOINCREMENT, pallet_name TEXT NOT NULL, customer_name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'Hazırlanıyor')""")

            # 8. YENİ: PERFORMANS İÇİN INDEX'LER
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_order_id ON production_logs(order_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_station ON production_logs(station_name)")
            except:
                pass

    # =========================================================================
    # BAŞLANGIÇ VERİLERİ
    # =========================================================================
    def init_machine_capacities(self):
        defaults = {
            "INTERMAC": 800, "LIVA KESIM": 800, "LAMINE KESIM": 600,
            "CNC RODAJ": 100, "DOUBLEDGER": 400, "ZIMPARA": 300,
            "TESIR A1": 400, "TESIR B1": 400, "TESIR B1-1": 400, "TESIR B1-2": 400,
            "DELİK": 200, "OYGU": 200,
            "TEMPER A1": 550, "TEMPER B1": 750, "TEMPER BOMBE": 300,
            "LAMINE A1": 250, "ISICAM B1": 500, "SEVKİYAT": 5000
        }
        with self.get_connection() as conn:
            for name, cap in defaults.items():
                try: conn.execute("INSERT INTO factory_settings (setting_key, setting_value) VALUES (?, ?)", (name, cap))
                except sqlite3.IntegrityError: pass

    def init_default_stocks(self):
        defaults = [("4mm Düz Cam", 1000, 200), ("6mm Düz Cam", 1000, 200)]
        with self.get_connection() as conn:
            for n, q, l in defaults:
                try: conn.execute("INSERT INTO stocks (product_name, quantity_m2, min_limit) VALUES (?, ?, ?)", (n, q, l))
                except: pass

    def init_default_prices(self):
        defaults = [("4mm Düz Cam", 100, "HAMMADDE"), ("KESİM İŞÇİLİK", 10, "İŞLEM")]
        with self.get_connection() as conn:
            for n, p, c in defaults:
                try: conn.execute("INSERT INTO unit_prices (item_name, price_per_m2, category) VALUES (?, ?, ?)", (n, p, c))
                except: pass

    def create_default_users(self):
        """Varsayılan kullanıcıları oluştur"""
        with self.get_connection() as conn:
            try:
                # Güvenlik modülü varsa PBKDF2, yoksa SHA256 kullan
                if SECURITY_AVAILABLE:
                    admin_hash = password_manager.hash_password("1234")
                    op_hash = password_manager.hash_password("0000")
                else:
                    admin_hash = hashlib.sha256("1234".encode()).hexdigest()
                    op_hash = hashlib.sha256("0000".encode()).hexdigest()
                
                conn.execute("INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)", 
                           ("admin", admin_hash, "admin", "Sistem Yöneticisi"))
                conn.execute("INSERT INTO users (username, password_hash, role, full_name, station_name) VALUES (?, ?, ?, ?, ?)", 
                           ("temper_usta", op_hash, "operator", "Ahmet Usta", "TEMPER A1"))
            except: 
                pass

    # =========================================================================
    # KULLANICI İŞLEMLERİ
    # =========================================================================
    def check_login(self, username, password):
        """Kullanıcı girişi - Hem eski SHA256 hem yeni PBKDF2 destekler"""
        with self.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            
            if not user:
                if SECURITY_AVAILABLE:
                    logger.warning("Giriş başarısız - kullanıcı bulunamadı", user=username)
                return None
            
            stored_hash = user['password_hash']
            
            # Güvenlik modülü varsa gelişmiş doğrulama
            if SECURITY_AVAILABLE:
                if password_manager.verify_password(password, stored_hash):
                    # Eski hash ise otomatik güncelle
                    if password_manager.is_legacy_hash(stored_hash):
                        new_hash = password_manager.hash_password(password)
                        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
                        logger.info("Kullanıcı şifresi güvenli formata güncellendi", user=username)
                    
                    logger.user_login(username, user['role'], success=True)
                    return dict(user)
                else:
                    logger.user_login(username, user['role'], success=False)
                    return None
            else:
                # Eski sistem (fallback)
                pwd_hash = hashlib.sha256(password.encode()).hexdigest()
                if stored_hash == pwd_hash:
                    return dict(user)
                return None

    def get_all_users(self):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("SELECT id, username, full_name, role, station_name FROM users").fetchall()]

    def add_new_user(self, u, p, r, f, s):
        """Yeni kullanıcı ekle"""
        # Güvenlik modülü varsa PBKDF2, yoksa SHA256 kullan
        if SECURITY_AVAILABLE:
            ph = password_manager.hash_password(p)
        else:
            ph = hashlib.sha256(p.encode()).hexdigest()
        
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO users (username, password_hash, role, full_name, station_name) VALUES (?, ?, ?, ?, ?)", (u, ph, r, f, s))
                if SECURITY_AVAILABLE:
                    logger.info("Yeni kullanıcı oluşturuldu", user=u, role=r)
                return True, "Ok"
            except Exception as e: 
                return False, str(e)

    def delete_user(self, uid):
        if uid == 1: return False
        with self.get_connection() as conn: 
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
            if SECURITY_AVAILABLE:
                logger.info("Kullanıcı silindi", user_id=uid)
        return True

    def change_password(self, user_id, new_password):
        """Şifre değiştir"""
        if SECURITY_AVAILABLE:
            new_hash = password_manager.hash_password(new_password)
        else:
            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        with self.get_connection() as conn:
            try:
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
                if SECURITY_AVAILABLE:
                    logger.info("Şifre değiştirildi", user_id=user_id)
                return True
            except:
                return False

    # =========================================================================
    # STOK İŞLEMLERİ
    # =========================================================================
    def get_all_stocks(self):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("SELECT * FROM stocks ORDER BY product_name").fetchall()]

    def get_stock_quantity(self, p_name):
        with self.get_connection() as conn:
            r = conn.execute("SELECT quantity_m2 FROM stocks WHERE product_name=?", (p_name,)).fetchone()
            return r[0] if r else 0

    def add_stock(self, p_name, amount):
        with self.get_connection() as conn:
            if conn.execute("SELECT id FROM stocks WHERE product_name=?", (p_name,)).fetchone():
                conn.execute("UPDATE stocks SET quantity_m2 = quantity_m2 + ? WHERE product_name=?", (amount, p_name))
            else:
                conn.execute("INSERT INTO stocks (product_name, quantity_m2, min_limit) VALUES (?, ?, 100)", (p_name, amount))

    def update_stock(self, product_name, quantity):
        """Stok güncelle"""
        with self.get_connection() as conn:
            conn.execute("UPDATE stocks SET quantity_m2 = ?, last_updated = CURRENT_TIMESTAMP WHERE product_name = ?", 
                        (quantity, product_name))

    def delete_stock(self, stock_id):
        """Stok sil"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))

    def get_low_stocks(self):
        """Minimum limiti altındaki stokları getir"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM stocks WHERE quantity_m2 < min_limit ORDER BY product_name"
            ).fetchall()]

    # =========================================================================
    # SİPARİŞ İŞLEMLERİ
    # =========================================================================
    def add_new_order(self, data):
        """Yeni sipariş ekle"""
        if data.get('total_m2', 0) > 0: 
            total_m2 = data['total_m2']
        else: 
            total_m2 = (data.get('width', 0) * data.get('height', 0) * data.get('quantity', 0)) / 10000.0
        
        sale_unit = data.get('sale_price', 0)
        total_sale = sale_unit * data.get('quantity', 0)

        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO orders (order_code, customer_name, product_type, thickness, quantity, 
                                       delivery_date, priority, status, width, height, route, 
                                       sale_price, total_price, declared_total_m2) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Beklemede', ?, ?, ?, ?, ?, ?)
                """, (
                    data['code'], data['customer'], data['product'], data['thickness'], 
                    data['quantity'], data['date'], data['priority'], 
                    data.get('width', 0), data.get('height', 0), 
                    data.get('route', 'KESİM,SEVKİYAT'), sale_unit, total_sale, total_m2
                ))
                
                p_name = f"{data['thickness']}mm {data['product']}"
                conn.execute("UPDATE stocks SET quantity_m2 = quantity_m2 - ? WHERE product_name = ?", (total_m2, p_name))
                
                if SECURITY_AVAILABLE:
                    logger.order_created(conn.execute("SELECT last_insert_rowid()").fetchone()[0], 
                                        data['customer'], total_m2)
                return True
            except Exception as e:
                print(f"Hata: {e}")
                if SECURITY_AVAILABLE:
                    logger.error(f"Sipariş ekleme hatası: {e}")
                return False

    def add_order(self, data: dict):
        """Yeni sipariş ekle (alternatif metod)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO orders (order_code, barcode, customer_name, product_type, thickness, 
                                   width, height, quantity, declared_total_m2, route, 
                                   sale_price, total_price, currency, priority, delivery_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('order_code'), data.get('barcode'), data.get('customer_name'),
                data.get('product_type'), data.get('thickness'),
                data.get('width'), data.get('height'), data.get('quantity', 1),
                data.get('declared_total_m2', 0), data.get('route'),
                data.get('sale_price', 0), data.get('total_price', 0),
                data.get('currency', 'TL'), data.get('priority', 'Normal'),
                data.get('delivery_date')
            ))
            order_id = cursor.lastrowid
            if SECURITY_AVAILABLE:
                logger.order_created(order_id, data.get('customer_name', ''), data.get('declared_total_m2', 0))
            return order_id

    def get_all_orders(self):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()]

    def get_orders_by_status(self, status):
        """Duruma göre siparişleri getir - liste veya tekil değer destekler"""
        with self.get_connection() as conn:
            if isinstance(status, (list, tuple)):
                placeholders = ','.join(['?'] * len(status))
                return [dict(r) for r in conn.execute(
                    f"SELECT * FROM orders WHERE status IN ({placeholders}) ORDER BY CASE priority WHEN 'Kritik' THEN 1 WHEN 'Acil' THEN 2 ELSE 3 END, created_at DESC", 
                    tuple(status)
                ).fetchall()]
            else:
                return [dict(r) for r in conn.execute(
                    "SELECT * FROM orders WHERE status = ? ORDER BY CASE priority WHEN 'Kritik' THEN 1 WHEN 'Acil' THEN 2 ELSE 3 END, created_at DESC", 
                    (status,)
                ).fetchall()]

    def get_active_orders(self):
        """Aktif siparişleri getir"""
        return self.get_orders_by_status(['Beklemede', 'Üretimde'])

    def search_orders(self, keyword):
        """Sipariş ara"""
        k = f"%{keyword}%"
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM orders WHERE order_code LIKE ? OR customer_name LIKE ? ORDER BY created_at DESC", 
                (k, k)
            ).fetchall()]

    def update_order_status(self, oid, st):
        with self.get_connection() as conn: 
            conn.execute("UPDATE orders SET status=? WHERE id=?", (st, oid))
            if SECURITY_AVAILABLE and st == 'Tamamlandı':
                logger.order_completed(oid)

    def update_order(self, order_id, data: dict):
        """Sipariş güncelle"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE orders SET 
                    customer_name=?, product_type=?, thickness=?, width=?, height=?,
                    quantity=?, declared_total_m2=?, route=?, sale_price=?, total_price=?,
                    currency=?, priority=?, delivery_date=?
                WHERE id=?
            """, (
                data.get('customer_name'), data.get('product_type'), data.get('thickness'),
                data.get('width'), data.get('height'), data.get('quantity'),
                data.get('declared_total_m2'), data.get('route'),
                data.get('sale_price'), data.get('total_price'),
                data.get('currency'), data.get('priority'), data.get('delivery_date'),
                order_id
            ))
            if SECURITY_AVAILABLE:
                logger.order_updated(order_id, "Sipariş güncellendi")

    def delete_order(self, order_id):
        """Sipariş sil"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM production_logs WHERE order_id=?", (order_id,))
            conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
            if SECURITY_AVAILABLE:
                logger.info("Sipariş silindi", order_id=order_id)

    def get_order_by_id(self, order_id):
        with self.get_connection() as conn:
            r = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            return dict(r) if r else None

    def get_order_by_code(self, order_code):
        """Sipariş koduna göre sipariş bilgilerini getir"""
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT id, order_code, customer_name, product_type, thickness,
                       width, height, quantity, declared_total_m2, priority, delivery_date,
                       route, status, sale_price
                FROM orders
                WHERE order_code = ?
            """, (order_code,)).fetchone()

            if not result:
                return None

            return {
                'id': result[0],
                'code': result[1],
                'customer': result[2],
                'product': result[3],
                'thickness': result[4],
                'width': result[5],
                'height': result[6],
                'quantity': result[7],
                'total_m2': result[8],
                'priority': result[9],
                'date': result[10],
                'route': result[11],
                'status': result[12],
                'sale_price': result[13]
            }

    def get_orders_list(self, status_filter=None):
        """Siparişleri listele"""
        with self.get_connection() as conn:
            if status_filter:
                return [dict(r) for r in conn.execute("SELECT * FROM orders WHERE status=? ORDER BY delivery_date", (status_filter,)).fetchall()]
            return [dict(r) for r in conn.execute("SELECT * FROM orders ORDER BY delivery_date").fetchall()]

    # =========================================================================
    # ÜRETİM VE LOGLAR
    # =========================================================================
    def register_production(self, order_id, station_name, qty_done, operator_name="Sistem"):
        """Parçalı Üretim Kaydı"""
        with self.get_connection() as conn:
            # Log kaydı
            conn.execute("""
                INSERT INTO production_logs (order_id, station_name, action, quantity, operator_name) 
                VALUES (?, ?, 'Tamamlandi', ?, ?)
            """, (order_id, station_name, qty_done, operator_name))

            # Tüm istasyonlar tamamlandı mı kontrol et
            if self._check_all_stations_completed(order_id):
                conn.execute("UPDATE orders SET status = 'Tamamlandı' WHERE id = ?", (order_id,))
                if SECURITY_AVAILABLE:
                    logger.order_completed(order_id)
            else:
                conn.execute("UPDATE orders SET status = 'Üretimde' WHERE id = ? AND status NOT IN ('Tamamlandı', 'Sevk Edildi')", (order_id,))
        
        if SECURITY_AVAILABLE:
            logger.production_completed(order_id, station_name, qty_done)

    def log_production(self, order_id, station, action, qty, operator):
        """Üretim logu ekle"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO production_logs (order_id, station_name, action, quantity, operator_name) 
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, station, action, qty, operator))
            if SECURITY_AVAILABLE:
                logger.production_started(order_id, station, operator)

    def complete_station_process(self, order_id, station_name):
        """Bir istasyonu tamamen bitirme"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO production_logs (order_id, station_name, action, quantity, operator_name) 
                VALUES (?, ?, 'Tamamlandi', 0, 'Sistem')
            """, (order_id, station_name))

            # Tüm istasyonlar tamamlandı mı kontrol et
            if self._check_all_stations_completed(order_id):
                conn.execute("UPDATE orders SET status = 'Tamamlandı' WHERE id = ?", (order_id,))
            else:
                conn.execute("UPDATE orders SET status = 'Üretimde' WHERE id = ? AND status NOT IN ('Tamamlandı', 'Sevk Edildi')", (order_id,))

    def report_fire(self, oid, qty, station_name="Bilinmiyor", operator_name="Sistem"):
        """Fire bildirimi"""
        with self.get_connection() as conn: 
            # Fire logu ekle
            conn.execute("""
                INSERT INTO production_logs (order_id, station_name, action, quantity, operator_name)
                VALUES (?, ?, 'Fire/Kırık', ?, ?)
            """, (oid, station_name, qty, operator_name))
            
            # Siparis fire sayisini artir
            conn.execute("UPDATE orders SET rework_count = rework_count + ?, has_breakage=1 WHERE id=?", (qty, oid))
        
        if SECURITY_AVAILABLE:
            logger.warning(f"Fire bildirimi: Siparis {oid}, {qty} adet", station=station_name)

    def get_station_progress(self, order_id, station_name):
        with self.get_connection() as conn:
            r = conn.execute("""
                SELECT SUM(quantity) FROM production_logs 
                WHERE order_id = ? AND station_name = ? AND action = 'Tamamlandi'
            """, (order_id, station_name)).fetchone()
            return r[0] if r[0] else 0

    def get_completed_stations_list(self, order_id):
        with self.get_connection() as conn:
            res = conn.execute("SELECT quantity FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not res: return []
            target = res[0]
            rows = conn.execute("""
                SELECT station_name, SUM(quantity) FROM production_logs 
                WHERE order_id = ? AND action='Tamamlandi' GROUP BY station_name
            """, (order_id,)).fetchall()

            completed = []
            for row in rows:
                if row[1] >= target:
                    completed.append(row[0])
            return completed

    def get_completed_stations(self, order_code):
        """Sipariş koduna göre tamamlanan istasyonları getir"""
        with self.get_connection() as conn:
            result = conn.execute("SELECT id FROM orders WHERE order_code = ?", (order_code,)).fetchone()
            if not result:
                return []
            order_id = result[0]
            return self.get_completed_stations_list(order_id)

    def _check_all_stations_completed(self, order_id):
        """Siparişin tüm istasyonları tamamlandı mı kontrol et"""
        with self.get_connection() as conn:
            order = conn.execute("SELECT route FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order or not order['route']:
                return False

            route_stations = [s.strip() for s in order['route'].split(',') if s.strip()]
            completed_stations = self.get_completed_stations_list(order_id)

            for station in route_stations:
                if station not in completed_stations:
                    return False

            return True

    def check_and_update_completion(self, order_id):
        """Sipariş tamamlanma kontrolü ve güncelleme"""
        if self._check_all_stations_completed(order_id):
            self.update_order_status(order_id, 'Tamamlandı')
            return True
        return False

    # =========================================================================
    # MATRİS VE DASHBOARD
    # =========================================================================
    def get_production_matrix_advanced(self):
        """Gelişmiş üretim matrisi - Karar destek için"""
        with self.get_connection() as conn:
            orders = conn.execute("""
                SELECT id, order_code, customer_name, route, quantity, priority, 
                       delivery_date, declared_total_m2, status, created_at
                FROM orders WHERE status NOT IN ('Sevk Edildi', 'Hatalı/Fire')
                ORDER BY 
                    CASE priority 
                        WHEN 'Kritik' THEN 1 
                        WHEN 'Acil' THEN 2 
                        WHEN 'Yüksek' THEN 3 
                        WHEN 'Normal' THEN 4 
                        ELSE 5 
                    END,
                    delivery_date ASC
            """).fetchall()
            
            data = []
            all_stations = [
                "INTERMAC", "LIVA KESIM", "LAMINE KESIM",
                "CNC RODAJ", "DOUBLEDGER", "ZIMPARA",
                "TESIR A1", "TESIR B1", "TESIR B1-1", "TESIR B1-2",
                "DELİK", "OYGU",
                "TEMPER A1", "TEMPER B1", "TEMPER BOMBE",
                "LAMINE A1", "ISICAM B1",
                "SEVKİYAT"
            ]
            
            for order in orders:
                oid = order['id']
                total = order['quantity']
                route = order['route'] or ""
                status_map = {}
                
                for st in all_stations:
                    if st not in route:
                        status_map[st] = {"status": "Yok", "done": 0, "total": 0}
                    else:
                        done = self.get_station_progress(oid, st)
                        if done >= total:
                            status_map[st] = {"status": "Bitti", "done": done, "total": total}
                        elif done > 0:
                            status_map[st] = {"status": "Kısmi", "done": done, "total": total}
                        else:
                            status_map[st] = {"status": "Bekliyor", "done": 0, "total": total}
                
                data.append({
                    "id": oid, 
                    "code": order['order_code'], 
                    "customer": order['customer_name'], 
                    "quantity": total,
                    "route": route,
                    "priority": order['priority'],
                    "delivery_date": order['delivery_date'],
                    "m2": order['declared_total_m2'] or 0,
                    "status": order['status'],
                    "created_at": order['created_at'],
                    "status_map": status_map
                })
            return data

    def get_master_production_table(self):
        """Master üretim tablosu"""
        return self.get_production_matrix_advanced()

    def get_dashboard_stats(self):
        with self.get_connection() as conn:
            active = conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Beklemede', 'Üretimde')").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'Tamamlandı'").fetchone()[0]
            fire = conn.execute("SELECT SUM(rework_count) FROM orders").fetchone()[0] or 0
            urgent = conn.execute("SELECT COUNT(*) FROM orders WHERE priority IN ('Acil', 'Kritik') AND status != 'Tamamlandı'").fetchone()[0]
            return {"active": active, "completed": completed, "fire": fire, "urgent": urgent}

    def get_station_loads(self):
        CAPACITIES = self.get_all_capacities()
        loads = {k: 0.0 for k in CAPACITIES.keys()}
        with self.get_connection() as conn:
            orders = conn.execute("""
                SELECT id, width, height, quantity, route, declared_total_m2 
                FROM orders WHERE status != 'Tamamlandı'
            """).fetchall()
            for r in orders:
                if r['declared_total_m2'] > 0: 
                    m2 = r['declared_total_m2']
                else: 
                    m2 = (r['width']*r['height']*r['quantity'])/10000.0 if r['width'] else 0
                
                completed = self.get_completed_stations_list(r['id'])
                route = r['route'] or ""
                
                for st in CAPACITIES.keys():
                    if st in route and st not in completed:
                        loads[st] += m2
        res = []
        ordered_keys = [
            "INTERMAC", "LIVA KESIM", "LAMINE KESIM", "CNC RODAJ", "DOUBLEDGER", "ZIMPARA",
            "TESIR A1", "TESIR B1", "TESIR B1-1", "TESIR B1-2", "DELİK", "OYGU",
            "TEMPER A1", "TEMPER B1", "TEMPER BOMBE", "LAMINE A1", "ISICAM B1", "SEVKİYAT"
        ]
        for station in ordered_keys:
            if station in CAPACITIES:
                limit = CAPACITIES[station]
                if limit <= 0: limit = 1
                percent = int((loads[station] / limit) * 100)
                status = "Normal"
                if percent > 90: status = "Kritik"
                elif percent > 70: status = "Yoğun"
                res.append({"name": station, "percent": min(percent, 100), "real_percent": percent, "status": status})
        return res

    # =========================================================================
    # RAPORLAMA VE ANALİZ
    # =========================================================================
    def get_system_logs(self, limit=1000):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("""
                SELECT pl.id, pl.timestamp, pl.operator_name, pl.station_name, pl.action, 
                       o.order_code, o.customer_name 
                FROM production_logs pl 
                LEFT JOIN orders o ON pl.order_id = o.id 
                ORDER BY pl.timestamp DESC LIMIT ?
            """, (limit,)).fetchall()]

    def search_logs(self, k):
        s = f"%{k}%"
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("""
                SELECT pl.id, pl.timestamp, pl.operator_name, pl.station_name, pl.action, 
                       o.order_code, o.customer_name 
                FROM production_logs pl 
                LEFT JOIN orders o ON pl.order_id = o.id 
                WHERE o.order_code LIKE ? OR pl.operator_name LIKE ? 
                ORDER BY pl.timestamp DESC
            """, (s, s)).fetchall()]

    def get_production_report_data(self, d1, d2):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("""
                SELECT pl.timestamp as islem_tarihi, o.order_code as siparis_no, 
                       o.customer_name as musteri, pl.station_name as istasyon, 
                       pl.action as islem, pl.operator_name as operator 
                FROM production_logs pl 
                JOIN orders o ON pl.order_id = o.id 
                WHERE date(pl.timestamp) BETWEEN ? AND ? 
                ORDER BY pl.timestamp DESC
            """, (d1, d2)).fetchall()]

    def get_order_lifecycle(self, code):
        with self.get_connection() as conn:
            o = conn.execute("""
                SELECT id, order_code, customer_name, route, status, quantity, 
                       declared_total_m2, width, height 
                FROM orders WHERE order_code = ?
            """, (code,)).fetchone()
            if not o: return None
            
            logs = conn.execute("""
                SELECT station_name, operator_name, timestamp, action 
                FROM production_logs WHERE order_id = ? ORDER BY timestamp ASC
            """, (o['id'],)).fetchall()
            
            st_prog = {}
            route_list = o['route'].split(',') if o['route'] else []
            for st in route_list:
                st = st.strip()
                done = self.get_station_progress(o['id'], st)
                total = o['quantity']
                st_prog[st] = {"done_qty": done, "total_qty": total, "is_finished": (done >= total)}
            
            return {"info": dict(o), "logs": [dict(r) for r in logs], "progress": st_prog}

    def get_operator_performance(self, days=30):
        """Operatör performans verisi"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT operator_name, COUNT(*) as islem_sayisi, SUM(quantity) as toplam_adet
                FROM production_logs 
                WHERE timestamp >= date('now', '-' || ? || ' days')
                AND operator_name IS NOT NULL AND operator_name != ''
                GROUP BY operator_name 
                ORDER BY toplam_adet DESC
            """, (days,)).fetchall()]

    def get_fire_analysis_data(self):
        """Fire analiz verisi"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT station_name, SUM(quantity) as fire_adedi
                FROM production_logs 
                WHERE action LIKE '%Fire%' OR action LIKE '%Hata%' OR action LIKE '%Kırık%'
                GROUP BY station_name 
                ORDER BY fire_adedi DESC
            """).fetchall()]

    # =========================================================================
    # KAPASİTE VE AYARLAR
    # =========================================================================
    def get_all_capacities(self):
        with self.get_connection() as conn:
            d = {r[0]: r[1] for r in conn.execute("SELECT setting_key, setting_value FROM factory_settings").fetchall()}
            if not d: 
                self.init_machine_capacities()
                return self.get_all_capacities()
            return d

    def update_capacity(self, m, v):
        with self.get_connection() as conn: 
            conn.execute("UPDATE factory_settings SET setting_value=? WHERE setting_key=?", (v, m))

    # =========================================================================
    # FİYAT İŞLEMLERİ
    # =========================================================================
    def get_all_prices(self):
        """Tüm fiyatları getir"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM unit_prices ORDER BY category, item_name").fetchall()]

    def update_price(self, item_name, new_price):
        """Fiyat güncelle"""
        with self.get_connection() as conn:
            conn.execute("UPDATE unit_prices SET price_per_m2 = ? WHERE item_name = ?", (new_price, item_name))

    def add_price(self, item_name, price, category):
        """Yeni fiyat ekle"""
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO unit_prices (item_name, price_per_m2, category) VALUES (?, ?, ?)", 
                           (item_name, price, category))
                return True
            except:
                return False

    # =========================================================================
    # SEVKİYAT İŞLEMLERİ
    # =========================================================================
    def get_ready_to_ship_orders(self):
        """Sevke hazır siparişleri getir (sadece 'Tamamlandı' durumunda olanlar)"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT * FROM orders 
                WHERE status = 'Tamamlandı' AND (pallet_id IS NULL OR pallet_id = 0) 
                ORDER BY order_code
            """).fetchall()]

    def get_active_pallets(self):
        with self.get_connection() as conn: 
            return [dict(r) for r in conn.execute("SELECT * FROM shipments WHERE status = 'Hazırlanıyor'").fetchall()]

    def create_pallet(self, n, c):
        with self.get_connection() as conn: 
            conn.execute("INSERT INTO shipments (pallet_name, customer_name) VALUES (?, ?)", (n, c))
            return 1

    def add_order_to_pallet(self, oid, pid):
        with self.get_connection() as conn: 
            conn.execute("UPDATE orders SET pallet_id=? WHERE id=?", (pid, oid))

    def ship_pallet(self, pid):
        with self.get_connection() as conn:
            conn.execute("UPDATE shipments SET status='Sevk Edildi' WHERE id=?", (pid,))
            conn.execute("UPDATE orders SET status='Sevk Edildi' WHERE pallet_id=?", (pid,))

    def get_shipped_pallets(self):
        """Sevk edilmiş sehpaları getir"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT * FROM shipments WHERE status = 'Sevk Edildi' ORDER BY created_at DESC
            """).fetchall()]

    def get_shipped_orders(self):
        """Sevk edilmiş siparişleri getir"""
        with self.get_connection() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT * FROM orders WHERE status = 'Sevk Edildi' ORDER BY order_code DESC
            """).fetchall()]

    # =========================================================================
    # BAKIM FONKSİYONLARI
    # =========================================================================
    def update_all_order_statuses(self):
        """Tüm siparişlerin durumlarını güncelle (bakım fonksiyonu)"""
        with self.get_connection() as conn:
            orders = conn.execute("""
                SELECT id, status FROM orders 
                WHERE status NOT IN ('Sevk Edildi', 'Hatalı/Fire')
            """).fetchall()

            updated_count = 0
            for order in orders:
                order_id = order['id']
                current_status = order['status']

                if self._check_all_stations_completed(order_id):
                    if current_status != 'Tamamlandı':
                        conn.execute("UPDATE orders SET status = 'Tamamlandı' WHERE id = ?", (order_id,))
                        updated_count += 1
                        print(f"Sipariş {order_id} -> Tamamlandı")
                elif current_status == 'Beklemede':
                    pass
                else:
                    if current_status != 'Üretimde':
                        conn.execute("UPDATE orders SET status = 'Üretimde' WHERE id = ?", (order_id,))
                        updated_count += 1

            return updated_count


# Global instance
db = DatabaseManager()