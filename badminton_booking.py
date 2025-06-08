import requests
from bs4 import BeautifulSoup
import datetime
import time
import json
import os
from urllib.parse import urlencode

def load_credentials():
    """从配置文件加载用户凭据"""
    config_file = 'credentials.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return None

def save_credentials(username, password):
    """保存用户凭据到配置文件"""
    config_file = 'credentials.json'
    try:
        with open(config_file, 'w') as f:
            json.dump({'username': username, 'password': password}, f)
        print("✅ 凭据已保存")
    except Exception as e:
        print(f"保存配置文件失败: {e}")

class MelbourneUniBadmintonBooking:
    def __init__(self):
        self.base_url = "https://unimelb.perfectmind.com"
        self.login_url = f"{self.base_url}/SocialSite/MemberRegistration/MemberSignIn"
        self.map_url = f"{self.base_url}/32617/Clients/BookMe4FacilityMap/Map"
        self.get_facilities_url = f"{self.base_url}/32617/Clients/BookMe4FacilityMap/GetFacilities"
        self.facility_page_url = f"{self.base_url}/32617/Clients/BookMe4LandingPages/Facility"
        self.facility_availability_url = f"{self.base_url}/32617/Clients/BookMe4LandingPages/FacilityAvailability"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': self.base_url,
            'Referer': self.map_url,
        }
        self.session.headers.update(self.headers)
        self.is_logged_in = False

    def login(self, username: str, password: str) -> bool:
        try:
            # 获取登录页面，获取token
            login_page = self.session.get(self.login_url)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            token = token_input['value'] if token_input else ''
            login_data = {
                'Username': username,
                'Password': password,
                '__RequestVerificationToken': token
            }
            resp = self.session.post(self.login_url, data=login_data, allow_redirects=True)
            if "SignOut" in resp.text or "signout" in resp.text:
                self.is_logged_in = True
                print("登录成功！")
                return True
            else:
                print("登录失败，请检查用户名和密码。")
                return False
        except Exception as e:
            print(f"登录异常: {e}")
            return False

    def get_token_and_ids(self):
        # 访问场地页面，获取token和ids
        resp = self.session.get(self.map_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        token = token_input['value'] if token_input else ''
        
        calendarId = "bce15730-1f38-4e5c-889c-856322a7f877"
        widgetId = "15f6af07-39c5-473e-b053-96653f77a406"
        mapId = "7d8b8d20-b7cf-43ac-8167-0738142baff3"
        return token, calendarId, widgetId, mapId

    def get_available_courts(self, start_date=None, end_date=None):
        if not self.is_logged_in:
            print("请先登录！")
            return []
        if not start_date:
            start_date = datetime.datetime.now().strftime('%Y%m%d')
        if not end_date:
            end_date = start_date
        token, calendarId, widgetId, mapId = self.get_token_and_ids()
        def date_to_ticks(date_str, hour=0, minute=0):
            dt = datetime.datetime.strptime(date_str, "%Y%m%d")
            dt = dt.replace(hour=hour, minute=minute)
            return str(int(dt.timestamp() * 1000))
        StartTimeInTicks = date_to_ticks(start_date, 0, 0)
        EndTimeInTicks = date_to_ticks(end_date, 23, 59)
        data = {
            "take": 10000,
            "skip": 0,
            "page": 1,
            "pageSize": 10000,
            "StartDate": start_date,
            "EndDate": end_date,
            "StartTimeInTicks": StartTimeInTicks,
            "EndTimeInTicks": EndTimeInTicks,
            "ShouldCheckAvailability": "true",
            "calendarId": calendarId,
            "widgetId": widgetId,
            "mapId": mapId,
            "filtersLoaded": "false",
            "__RequestVerificationToken": token
        }
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
        resp = self.session.post(self.get_facilities_url, data=data, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print("获取场地信息失败", resp.status_code)
            return None

    def access_facility_page(self, facility_id, arrival_date=None):
        """访问具体的设施页面"""
        if not self.is_logged_in:
            print("请先登录！")
            return None
        
        if not arrival_date:
            arrival_date = datetime.datetime.now().isoformat() + 'Z'
        
        token, calendarId, widgetId, mapId = self.get_token_and_ids()
        
        # 构建设施页面URL参数
        params = {
            'facilityId': facility_id,
            'widgetId': widgetId,
            'calendarId': calendarId,
            'arrivalDate': arrival_date,
            'landingPageBackUrl': f"{self.base_url}/32617/Clients/BookMe4FacilityMap/Map?mapId={mapId}&widgetId={widgetId}&calendarId={calendarId}"
        }
        
        facility_url = f"{self.facility_page_url}?{urlencode(params)}"
        
        try:
            resp = self.session.get(facility_url)
            if resp.status_code == 200:
                return resp
            else:
                print(f"访问设施页面失败，状态码: {resp.status_code}")
                return None
        except Exception as e:
            print(f"访问设施页面异常: {e}")
            return None

    def get_facility_availability(self, facility_id, date_str=None, days_count=7):
        """获取具体设施的详细时间段可用性"""
        if not self.is_logged_in:
            return None
        
        if not date_str:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 先访问设施页面获取必要的token和参数
        arrival_date = f"{date_str}T14:00:00.000Z"
        facility_page_resp = self.access_facility_page(facility_id, arrival_date)
        
        if not facility_page_resp:
            return None
        
        # 从设施页面获取token和serviceId
        soup = BeautifulSoup(facility_page_resp.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        token = token_input['value'] if token_input else ''
        
        if not token:
            return None
        
        # 从JavaScript中提取serviceId和duration信息
        service_id = None
        duration_ids = []
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'services:' in script.string and 'Badminton Hire' in script.string:
                script_content = script.string
                # 查找服务ID
                import re
                # 查找 "ID":"xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" 模式，特别是Badminton Hire服务的ID
                id_pattern = r'"ID":"([a-f0-9-]{36})"[^}]*"Name":"Badminton Hire"'
                match = re.search(id_pattern, script_content)
                if match:
                    service_id = match.group(1)
                
                # 提取60分钟时长的DurationIDs
                duration_pattern = r'"Duration":60\.0[^}]*"DurationIDs":\[([^\]]+)\]'
                duration_match = re.search(duration_pattern, script_content)
                if duration_match:
                    # 提取DurationIDs数组
                    duration_ids_str = duration_match.group(1)
                    duration_ids = re.findall(r'"([a-f0-9-]{36})"', duration_ids_str)
                break
        
        if not service_id:
            service_id = "e413294c-507d-4653-b25e-c30c09be2e3f"  # 使用默认值
        
        if not duration_ids:
            duration_ids = [
                "393bd548-77a3-42db-8b10-02580516a1d6",
                "abfe26e9-3c74-4bf9-a82d-0ae8e99fd8d4",
                "b2645b1b-0c84-40d5-b39f-87f93eb06d53",
                "60887470-6f40-4743-833c-8b384b3e8df8"
            ]
        
        # 准备FacilityAvailability请求的数据
        import urllib.parse
        
        base_data = {
            'facilityId': facility_id,
            'date': date_str,
            'daysCount': str(days_count),
            'duration': '60',
            'serviceId': service_id,
            '__RequestVerificationToken': token
        }
        
        # 构建表单数据字符串，手动处理多个durationIds
        form_data = []
        for key, value in base_data.items():
            form_data.append(f"{urllib.parse.quote(key)}={urllib.parse.quote(str(value))}")
        
        # 添加多个durationIds[]参数
        for duration_id in duration_ids:
            form_data.append(f"durationIds%5B%5D={urllib.parse.quote(duration_id)}")
        
        form_data_str = '&'.join(form_data)
        
        # 设置请求头
        headers = self.headers.copy()
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': facility_page_resp.url
        })
        
        try:
            resp = self.session.post(self.facility_availability_url, 
                                   data=form_data_str, 
                                   headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                return None
        except Exception as e:
            return None

    def parse_date_from_json(self, date_str):
        """解析JSON日期格式 /Date(timestamp)/"""
        import re
        match = re.search(r'/Date\((\d+)\)/', date_str)
        if match:
            timestamp = int(match.group(1)) / 1000  # 转换为秒
            return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        return date_str

    def display_facility_time_slots(self, facility_id, facility_name, date_str=None, days_count=7):
        """显示具体设施的详细时间段信息"""
        availability_data = self.get_facility_availability(facility_id, date_str, days_count)
        
        if not availability_data:
            print(f"❌ 无法获取 {facility_name} 的时间段信息")
            return
        
        print(f"\n🏟️ {facility_name} - 可用时间段")
        print(f"📅 查询日期: {date_str} (未来{days_count}天)")
        
        # 解析可用时间段数据
        if isinstance(availability_data, dict):
            availabilities = availability_data.get('availabilities', [])
            
            if availabilities:
                for day_data in availabilities:
                    # 解析日期
                    date_raw = day_data.get('Date', '')
                    date_formatted = self.parse_date_from_json(date_raw)
                    
                    # 解析预订组
                    booking_groups = day_data.get('BookingGroups', [])
                    day_slots = []
                    
                    for group in booking_groups:
                        available_spots = group.get('AvailableSpots', [])
                        
                        for spot in available_spots:
                            if not spot.get('IsDisabled', False):
                                time_info = spot.get('Time', {})
                                duration_info = spot.get('Duration', {})
                                
                                start_hour = time_info.get('Hours', 0)
                                start_minute = time_info.get('Minutes', 0)
                                duration_hours = duration_info.get('TotalHours', 1)
                                
                                start_time = f"{start_hour:02d}:{start_minute:02d}"
                                end_hour = start_hour + int(duration_hours)
                                end_minute = start_minute + int((duration_hours % 1) * 60)
                                if end_minute >= 60:
                                    end_hour += 1
                                    end_minute -= 60
                                end_time = f"{end_hour:02d}:{end_minute:02d}"
                                
                                day_slots.append(f"{start_time}-{end_time}")
                    
                    if day_slots:
                        print(f"  📅 {date_formatted}: {', '.join(day_slots)}")
                    else:
                        print(f"  📅 {date_formatted}: 无可用时段")
            else:
                print("  ❌ 查询范围内无可用时段")
        
        print()

    def display_all_facilities_summary(self, date_str=None, days_count=3):
        """显示所有场地的可用时间段摘要"""
        if not date_str:
            date_str = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 获取所有场地信息
        facilities_data = self.get_available_courts()
        if not facilities_data or not facilities_data.get('facilities'):
            print("❌ 无法获取场地信息")
            return
        
        facilities = facilities_data['facilities']
        print(f"\n🏸 墨尔本大学羽毛球馆 - 场地可用性摘要")
        print(f"📅 查询日期: {date_str} (未来{days_count}天)")
        print("-" * 60)
        
        for facility in facilities:
            facility_id = facility.get('ID', '')
            facility_name = facility.get('Name', '未知场地')
            
            if facility_id:
                # 获取详细时间段
                availability_data = self.get_facility_availability(facility_id, date_str, days_count)
                
                if availability_data and availability_data.get('availabilities'):
                    availabilities = availability_data['availabilities']
                    total_days_with_slots = 0
                    total_slots = 0
                    
                    for day_data in availabilities:
                        booking_groups = day_data.get('BookingGroups', [])
                        day_slots = sum(len(group.get('AvailableSpots', [])) for group in booking_groups if group.get('AvailableSpots'))
                        # 只统计未被禁用的时段
                        available_slots = 0
                        for group in booking_groups:
                            for spot in group.get('AvailableSpots', []):
                                if not spot.get('IsDisabled', False):
                                    available_slots += 1
                        
                        if available_slots > 0:
                            total_days_with_slots += 1
                            total_slots += available_slots
                    
                    if total_slots > 0:
                        print(f"🏟️ {facility_name:<8} ✅ {total_days_with_slots}天有空档，共{total_slots}个时段")
                    else:
                        print(f"🏟️ {facility_name:<8} ❌ 暂无可用时段")
                else:
                    print(f"🏟️ {facility_name:<8} ❓ 查询失败")
                
                time.sleep(0.3)  # 避免请求过快
        
        print("-" * 60)

def main():
    booking = MelbourneUniBadmintonBooking()
    
    # 尝试加载保存的凭据
    credentials = load_credentials()
    
    if credentials:
        print("📝 发现保存的登录信息")
        use_saved = input("是否使用保存的登录信息？(y/n): ").lower().strip() == 'y'
        if use_saved:
            username = credentials['username']
            password = credentials['password']
        else:
            username = input("请输入用户名: ").strip()
            password = input("请输入密码: ").strip()
    else:
        username = input("请输入用户名: ").strip()
        password = input("请输入密码: ").strip()
    
    if not booking.login(username, password):
        print("❌ 登录失败，程序退出。")
        return
    
    # 询问是否保存凭据
    if not credentials or not use_saved:
        save_choice = input("是否保存登录信息？(y/n): ").lower().strip() == 'y'
        if save_choice:
            save_credentials(username, password)
    
    print("🏸 墨尔本大学羽毛球馆预订查询")
    
    # 获取用户输入的日期范围
    def get_date_input():
        while True:
            try:
                print("\n📅 请输入查询日期范围 (格式: YYYYMMDD)")
                start_date_str = input("请输入开始日期 (例如: 20250609): ").strip()
                end_date_str = input("请输入结束日期 (例如: 20250615): ").strip()
                
                # 验证日期格式
                if len(start_date_str) != 8 or len(end_date_str) != 8:
                    print("❌ 日期格式错误！请输入8位数字，例如: 20250609")
                    continue
                
                # 尝试解析日期
                start_date = datetime.datetime.strptime(start_date_str, '%Y%m%d')
                end_date = datetime.datetime.strptime(end_date_str, '%Y%m%d')
                
                # 检查日期顺序
                if start_date > end_date:
                    print("❌ 开始日期不能晚于结束日期！")
                    continue
                
                # 转换为不同格式供不同函数使用
                start_date_formatted = start_date.strftime('%Y-%m-%d')  # YYYY-MM-DD格式
                end_date_formatted = end_date.strftime('%Y-%m-%d')      # YYYY-MM-DD格式
                days_count = (end_date - start_date).days + 1           # 计算天数
                
                print(f"✅ 查询日期范围: {start_date_formatted} 至 {end_date_formatted} ({days_count}天)")
                return start_date_formatted, end_date_formatted, days_count, start_date_str, end_date_str
                
            except ValueError:
                print("❌ 日期格式错误！请输入有效的日期，格式: YYYYMMDD")
            except KeyboardInterrupt:
                print("\n👋 用户取消，程序退出。")
                return None, None, None, None, None
    
    date_result = get_date_input()
    if not date_result[0]:  # 用户取消
        return
    
    start_date_formatted, end_date_formatted, days_count, start_date_raw, end_date_raw = date_result
    
    # 显示所有场地摘要 - 使用YYYYMMDD格式和天数
    print(f"\n🔍 正在查询 {start_date_formatted} 至 {end_date_formatted} 的场地信息...")
    
    # 获取场地信息 - 使用原始YYYYMMDD格式
    facilities_data = booking.get_available_courts(start_date_raw, end_date_raw)
    if not facilities_data or not facilities_data.get('facilities'):
        print("❌ 无法获取场地信息")
        return
    
    facilities = facilities_data['facilities']
    print(f"\n🏸 墨尔本大学羽毛球馆 - 场地可用性摘要")
    print(f"📅 查询日期: {start_date_formatted} 至 {end_date_formatted} ({days_count}天)")
    print("-" * 60)
    
    # 显示场地摘要
    available_facilities = []
    for facility in facilities:
        facility_id = facility.get('ID', '')
        facility_name = facility.get('Name', '未知场地')
        
        if facility_id:
            # 获取详细时间段 - 使用YYYY-MM-DD格式
            availability_data = booking.get_facility_availability(facility_id, start_date_formatted, days_count)
            
            if availability_data and availability_data.get('availabilities'):
                availabilities = availability_data['availabilities']
                total_days_with_slots = 0
                total_slots = 0
                
                for day_data in availabilities:
                    booking_groups = day_data.get('BookingGroups', [])
                    # 只统计未被禁用的时段
                    available_slots = 0
                    for group in booking_groups:
                        for spot in group.get('AvailableSpots', []):
                            if not spot.get('IsDisabled', False):
                                available_slots += 1
                    
                    if available_slots > 0:
                        total_days_with_slots += 1
                        total_slots += available_slots
                
                if total_slots > 0:
                    print(f"🏟️ {facility_name:<8} ✅ {total_days_with_slots}天有空档，共{total_slots}个时段")
                    available_facilities.append((facility_id, facility_name))
                else:
                    print(f"🏟️ {facility_name:<8} ❌ 暂无可用时段")
            else:
                print(f"🏟️ {facility_name:<8} ❓ 查询失败")
            
            time.sleep(0.3)  # 避免请求过快
    
    print("-" * 60)
    
    # 显示有可用时段的场地的详细信息
    if available_facilities:
        print(f"\n📋 详细可用时间段:")
        
        for facility_id, facility_name in available_facilities:
            booking.display_facility_time_slots(facility_id, facility_name, start_date_formatted, days_count)
            time.sleep(0.2)  # 避免请求过快
    else:
        print(f"\n❌ 在 {start_date_formatted} 至 {end_date_formatted} 期间没有找到可用的羽毛球场地。")

if __name__ == "__main__":
    main() 
