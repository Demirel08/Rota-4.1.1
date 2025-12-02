import math
from datetime import datetime, timedelta
try:
    from core.db_manager import db
except ImportError:
    pass

class SmartPlanner:
    """
    AKILLI PLANLAMA MOTORU v14 (ETKİ ANALİZİ) 📉
    Yeni bir acil siparişin, mevcut kuyruğu nasıl etkilediğini hesaplar.
    """
    
    def __init__(self):
        self.FORECAST_DAYS = 30 
        
        try:
            self.capacities = db.get_all_capacities()
            if not self.capacities: raise ValueError
        except:
            self.capacities = {} 
        
        self.station_order = [
            "INTERMAC", "LIVA KESIM", "LAMINE KESIM",
            "CNC RODAJ", "DOUBLEDGER", "ZIMPARA",
            "TESIR A1", "TESIR B1", "TESIR B1-1", "TESIR B1-2",
            "DELİK", "OYGU",
            "TEMPER A1", "TEMPER B1", "TEMPER BOMBE",
            "LAMINE A1", "ISICAM B1",
            "SEVKİYAT"
        ]

    def fix_route_order(self, user_route_str):
        if not user_route_str: return ""
        selected = [s.strip() for s in user_route_str.split(',')]
        sorted_route = []
        for station in self.station_order:
            if station in selected:
                sorted_route.append(station)
        return ",".join(sorted_route)

    def _run_simulation(self, new_order=None):
        # 1. Mevcut İşleri Çek
        active_orders = db.get_orders_by_status(["Beklemede", "Üretimde"])
        
        # 2. Yeni Siparişi Ekle (Eğer varsa)
        target_order_code = None
        if new_order:
            simulated_order = {
                'id': -1,
                'order_code': '>>> HESAPLANAN <<<',
                'customer_name': 'YENİ',
                'width': new_order.get('width', 0),
                'height': new_order.get('height', 0),
                'quantity': new_order.get('quantity', 0),
                'declared_total_m2': new_order.get('total_m2', 0),
                'route': new_order.get('route', ''),
                'priority': new_order.get('priority', 'Normal'),
                'delivery_date': '9999-12-31',
                'is_new': True 
            }
            active_orders.append(simulated_order)

        # 3. SIRALAMA (4 SEVİYE)
        # Kritik(1) > Çok Acil(2) > Acil(3) > Normal(4)
        priority_map = {"Kritik": 1, "Çok Acil": 2, "Acil": 3, "Normal": 4}
        
        active_orders.sort(key=lambda x: (
            priority_map.get(x.get('priority', 'Normal'), 4), 
            str(x.get('delivery_date', '9999'))
        ))

        # 4. SİMÜLASYON DEĞİŞKENLERİ
        forecast_grid = {k: [0.0]*self.FORECAST_DAYS for k in self.capacities.keys()}
        loads_grid = {k: [0.0]*self.FORECAST_DAYS for k in self.capacities.keys()}
        details_grid = {k: [[] for _ in range(self.FORECAST_DAYS)] for k in self.capacities.keys()}
        machine_free_time = {k: 0.0 for k in self.capacities.keys()}
        
        # Siparişlerin tahmini bitiş günlerini saklayacak sözlük
        # { 'SIP-001': 2.5, 'SIP-002': 4.1 }
        order_finish_times = {} 
        target_finish_day = 0

        # 5. MOTOR ÇALIŞIYOR
        for order in active_orders:
            m2 = order.get('declared_total_m2', 0)
            if not m2 or m2 <= 0:
                w = order.get('width', 0)
                h = order.get('height', 0)
                q = order.get('quantity', 0)
                if w and h and q: m2 = (w * h * q) / 10000.0
            
            if m2 <= 0: continue
            
            total_qty = order.get('quantity', 1)
            route_str = order.get('route', '')
            route_steps = route_str.split(',')
            
            completed_stops = []
            if not order.get('is_new'):
                completed_stops = db.get_completed_stations_list(order['id'])
            
            current_order_ready_time = 0.0 
            
            for station in route_steps:
                station = station.strip()
                if station not in self.capacities: continue
                
                # Eğer istasyon bitmişse, o istasyonda zaman harcama
                # AMA sipariş o istasyondan çıktı sayılır, zaman akmaya devam eder.
                if station in completed_stops: continue 

                daily_cap = self.capacities[station]
                if daily_cap <= 0: daily_cap = 1
                
                done_qty = 0
                if not order.get('is_new'):
                    done_qty = db.get_station_progress(order['id'], station)
                
                remaining_ratio = 1.0 - (done_qty / total_qty)
                if remaining_ratio <= 0: continue

                remaining_m2 = m2 * remaining_ratio
                duration_days = remaining_m2 / daily_cap
                
                # MANTIK: 
                # Bu sipariş ne zaman başlayabilir?
                # 1. Kendisi hazır olmalı (Önceki makineden çıkmalı) -> current_order_ready_time
                # 2. Makine boş olmalı -> machine_free_time[station]
                start_day = max(current_order_ready_time, machine_free_time[station])
                end_day = start_day + duration_days
                
                # GANTT'A YAZ
                temp_start = start_day
                while temp_start < end_day:
                    day_idx = int(temp_start)
                    if day_idx >= self.FORECAST_DAYS: break 
                    
                    chunk_end = min(end_day, day_idx + 1)
                    work_amount = chunk_end - temp_start
                    
                    forecast_grid[station][day_idx] += (work_amount * 100)
                    loads_grid[station][day_idx] += (work_amount * daily_cap)
                    
                    info = {
                        "code": order['order_code'],
                        "customer": order.get('customer_name', 'Tahmini'),
                        "m2": remaining_m2
                    }
                    exists = any(x['code'] == info['code'] for x in details_grid[station][day_idx])
                    if not exists:
                        details_grid[station][day_idx].append(info)
                    
                    temp_start = chunk_end
                
                machine_free_time[station] = end_day
                current_order_ready_time = end_day
            
            # Siparişin Bitiş Gününü Kaydet
            order_code = order.get('order_code')
            order_finish_times[order_code] = current_order_ready_time
            
            if order.get('is_new'):
                target_finish_day = current_order_ready_time

        return forecast_grid, details_grid, loads_grid, target_finish_day, order_finish_times

    def calculate_forecast(self):
        try: self.capacities = db.get_all_capacities()
        except: pass
        grid, details, loads, _, _ = self._run_simulation(new_order=None)
        return grid, details, loads

    def calculate_impact(self, new_order_data):
        """
        ETKİ ANALİZİ 🧪
        Yeni siparişi eklemeden önce ve ekledikten sonraki durumu karşılaştırır.
        Geciken siparişleri listeler.
        """
        try: self.capacities = db.get_all_capacities()
        except: pass

        # 1. SENARYO: Yeni sipariş YOK (Baz Durum)
        _, _, _, _, base_finish_times = self._run_simulation(new_order=None)
        
        # 2. SENARYO: Yeni sipariş VAR (Etkilenmiş Durum)
        _, _, _, target_day, new_finish_times = self._run_simulation(new_order=new_order_data)
        
        # 3. KARŞILAŞTIRMA
        delayed_orders = []
        
        for code, base_time in base_finish_times.items():
            if code in new_finish_times:
                new_time = new_finish_times[code]
                # Eğer süre uzadıysa (Küçük farkları yoksay, >0.1 gün)
                diff = new_time - base_time
                if diff > 0.1:
                    delayed_orders.append({
                        "code": code,
                        "delay": math.ceil(diff), # Kaç gün gecikti?
                        "old_day": math.ceil(base_time),
                        "new_day": math.ceil(new_time)
                    })
        
        # Hedef siparişin bitiş tarihi
        today = datetime.now()
        delivery_date = today + timedelta(days=math.ceil(target_day))
        if delivery_date.weekday() == 6: delivery_date += timedelta(days=1)
        
        return delivery_date, math.ceil(target_day), delayed_orders

planner = SmartPlanner()